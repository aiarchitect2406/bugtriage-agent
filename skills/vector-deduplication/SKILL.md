---
name: vector-deduplication
description: Computes vector embeddings of sanitized error signatures and queries the issue index using cosine similarity to link duplicate alerts and suppress noise.
activation_cues:
  - "check_duplicate"
  - "vector_similarity"
  - "cluster_incident"
  - "dedupe_issues"
tools:
  - "query_similar_bugs_by_vector"
---

# Skill: Vector Deduplication & Incident Clustering

## Purpose
Generates normalized semantic embeddings from sanitized error messages and performs cosine similarity search against active open issues.

## Activation Protocol
Triggered immediately following log sanitization to verify if the incident is an existing known issue ($S \ge 0.85$) or a new regression.

## Tool Binding
Dynamically attaches and executes `query_similar_bugs_by_vector`.
