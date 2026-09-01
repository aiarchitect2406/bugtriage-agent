import os
import json
import math
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.models.bug_report import DedupeSearchResult
from app.config import Config

logger = logging.getLogger(__name__)


class PersistentBugStore:
    """Persistent storage connecting the agent to a database for cross-turn history and vector deduplication."""

    _store_path: str = os.getenv(
        "PERSISTENT_DB_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "tests",
            "fixtures",
            "data",
            "persistent_bugs.json",
        ),
    )
    _cache: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def _get_path(cls) -> str:
        db_path = cls._store_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        return db_path

    @classmethod
    def get_all_bugs(cls) -> List[Dict[str, Any]]:
        """Retrieves all bug records from the persistent database."""
        path = cls._get_path()
        if not os.path.exists(path):
            return list(cls._cache or [])
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    cls._cache = data
                    return list(data)
        except Exception as e:
            logger.debug(f"Persistent database read notice: {e}")
        return list(cls._cache or [])

    @classmethod
    def store_bug(
        cls,
        issue_id: str,
        title: str,
        description: str,
        stack_trace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persists a new bug entry to the database for cross-turn and cross-session retrieval."""
        path = cls._get_path()
        bugs = cls.get_all_bugs()

        for b in bugs:
            if b.get("issue_id") == issue_id:
                b["title"] = title
                b["description"] = description
                b["stack_trace"] = stack_trace
                b["metadata"] = metadata or {}
                cls._save_bugs(bugs, path)
                return b

        entry = {
            "issue_id": issue_id,
            "title": title,
            "description": description,
            "stack_trace": stack_trace,
            "metadata": metadata or {},
        }
        bugs.append(entry)
        cls._save_bugs(bugs, path)
        return entry

    @classmethod
    def _save_bugs(cls, bugs: List[Dict[str, Any]], path: str) -> None:
        cls._cache = bugs
        tmp_path = f"{path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(bugs, f, indent=2)
            os.replace(tmp_path, path)
        except Exception as e:
            logger.debug(f"Persistent database write notice: {e}")

    @classmethod
    def clear_store(cls) -> None:
        """Clears the persistent store (used primarily for test isolation)."""
        cls._cache = []
        path = cls._get_path()
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


class QuerySimilarBugsInput(BaseModel):
    """Input payload for vector duplicate search."""
    issue_id: str = Field(..., description="Target issue ID to check for duplicates")
    bug_title: str = Field(..., description="Title of the incoming bug report")
    bug_description: str = Field(..., description="Description/stack trace of the incoming bug")
    candidate_historical_bugs: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="Optional list of historical bug candidates"
    )

class QuerySimilarBugsOutput(BaseModel):
    """Output payload from vector similarity duplicate check."""
    status: str = Field(..., description="'SUCCESS' or 'ERROR'")
    dedupe_result: Optional[DedupeSearchResult] = Field(None, description="Detailed deduplication analysis")
    message: str = Field(..., description="Human-readable outcome summary")
    recovery_hint: Optional[str] = Field(None, description="Corrective action on failure")

def _compute_mock_embedding(text: str) -> List[float]:
    """Generates a normalized deterministic bag-of-words vector representation."""
    vocab = [
        "nullpointer", "address", "checkout", "payment", "token", 
        "auth", "login", "database", "timeout", "syntax", "deadlock"
    ]
    text_lower = text.lower()
    vec = [float(text_lower.count(word)) for word in vocab]
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return [0.0] * len(vocab)
    return [x / norm for x in vec]

def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two unit vectors."""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    return max(0.0, min(1.0, dot_product))

def query_similar_bugs_by_vector(
    issue_id: str,
    bug_title: str,
    bug_description: str,
    candidate_historical_bugs: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Queries vector database to identify semantically duplicate issues using cosine similarity.

    Args:
        issue_id: The unique identifier for the incoming bug report.
        bug_title: The title or summary of the bug report.
        bug_description: The description or stack trace text.
        candidate_historical_bugs: Optional list of historical bug records with keys
            'issue_id', 'title', and 'description'.

    Returns:
        Dict[str, Any]: A dictionary serialized from QuerySimilarBugsOutput containing
            status ('SUCCESS' or 'ERROR'), dedupe_result, message, and recovery_hint.

    Raises:
        None: All exceptions are caught and returned in the structured dictionary.
    """
    try:
        if not bug_title and not bug_description:
            return QuerySimilarBugsOutput(
                status="ERROR",
                message="Both bug_title and bug_description are empty.",
                recovery_hint="Ensure bug_title and bug_description contain descriptive text."
            ).model_dump()

        if candidate_historical_bugs is not None:
            candidates = list(candidate_historical_bugs)
        else:
            candidates = PersistentBugStore.get_all_bugs()

        # Check Vertex AI Search Datastore if configured
        datastore_id = os.environ.get("VERTEX_SEARCH_DATASTORE_ID")
        if datastore_id and not candidates:
            try:
                from google.cloud import discoveryengine_v1 as discoveryengine
                search_client = discoveryengine.SearchServiceClient()
                serving_config = (
                    f"projects/{Config.PROJECT_ID}/locations/{Config.GEAP_LOCATION}/"
                    f"collections/default_collection/dataStores/{datastore_id}/servingConfigs/default_search"
                )
                request = discoveryengine.SearchRequest(
                    serving_config=serving_config,
                    query=f"{bug_title} {bug_description}",
                    page_size=5,
                )
                response = search_client.search(request=request)
                for res in response.results:
                    doc = getattr(res, "document", None)
                    if doc and hasattr(doc, "struct_data"):
                        s_data = dict(doc.struct_data)
                        candidates.append({
                            "issue_id": s_data.get("issue_id", doc.id),
                            "title": s_data.get("title", ""),
                            "description": s_data.get("description", ""),
                        })
            except Exception as v_err:
                logger.debug(f"Vertex AI Search datastore query notice: {v_err}")


        target_text = f"{bug_title} {bug_description}"
        target_vec = _compute_mock_embedding(target_text)

        best_score = 0.0
        best_match_id = None
        best_match_title = None

        for cand in candidates:
            if cand.get("issue_id") == issue_id:
                continue
            cand_text = f"{cand.get('title', '')} {cand.get('description', '')}"
            cand_vec = _compute_mock_embedding(cand_text)
            sim = _cosine_similarity(target_vec, cand_vec)
            
            if sim > best_score:
                best_score = sim
                best_match_id = cand.get("issue_id")
                best_match_title = cand.get("title")

        threshold = Config.DUPLICATE_SIMILARITY_THRESHOLD
        is_duplicate = best_score >= threshold and best_match_id is not None

        if is_duplicate:
            explanation = (
                f"Duplicate detected: High semantic similarity ({best_score:.2f} >= {threshold:.2f}) "
                f"with existing issue {best_match_id} ('{best_match_title}')."
            )
        else:
            explanation = (
                f"No duplicate detected: Highest similarity score was {best_score:.2f} "
                f"(below threshold of {threshold:.2f})."
            )

        dedupe_result = DedupeSearchResult(
            is_duplicate=is_duplicate,
            matching_parent_issue_id=best_match_id if is_duplicate else None,
            similarity_score=round(best_score, 4),
            explanation=explanation
        )

        return QuerySimilarBugsOutput(
            status="SUCCESS",
            dedupe_result=dedupe_result,
            message=explanation
        ).model_dump()

    except Exception as e:
        return QuerySimilarBugsOutput(
            status="ERROR",
            message=f"Vector search failed: {str(e)}",
            recovery_hint="Verify that vector database is accessible and candidate lists are formatted correctly."
        ).model_dump()
