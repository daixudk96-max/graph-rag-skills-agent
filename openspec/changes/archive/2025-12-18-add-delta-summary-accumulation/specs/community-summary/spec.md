## ADDED Requirements

### Requirement: Delta Summary Generation
The system SHALL generate incremental delta summaries for community updates instead of regenerating full summaries when new entities are added to existing communities.

#### Scenario: New entity added to existing community
- **GIVEN** a community with an existing base summary
- **WHEN** an incremental update adds new entities to the community
- **THEN** the system generates a delta summary containing only the new information
- **AND** stores the delta as a `__CommunityDelta__` node linked to the community

#### Scenario: Delta summary content
- **WHEN** generating a delta summary
- **THEN** the summary describes what new information was added
- **AND** the summary does NOT re-read or include existing community content
- **AND** the delta token count is significantly smaller than a full summary

---

### Requirement: Read-Time Delta Merging
The system SHALL dynamically merge base summaries with pending delta summaries at query time to provide complete community context.

#### Scenario: Global search with pending deltas
- **GIVEN** a community with base summary and one or more pending deltas
- **WHEN** performing a global search query
- **THEN** the returned community content includes both base summary and delta summaries
- **AND** deltas are clearly marked (e.g., "[Recent Updates]" section)

#### Scenario: Community query with no deltas
- **GIVEN** a community with only a base summary (no pending deltas)
- **WHEN** querying community information
- **THEN** the return format remains unchanged from current behavior

---

### Requirement: Background Compaction
The system SHALL provide a background compaction mechanism to merge accumulated delta summaries into the base summary.

#### Scenario: Threshold-triggered compaction
- **GIVEN** a community with pending deltas exceeding the configured threshold
- **WHEN** compaction is triggered (threshold: delta count > 5 OR total tokens > 1000)
- **THEN** the system merges all deltas into the base summary via LLM fusion
- **AND** updates the community's `last_compacted_at` timestamp
- **AND** removes or marks the compacted delta nodes

#### Scenario: Manual compaction trigger
- **WHEN** an administrator triggers manual compaction for a specific community
- **THEN** compaction proceeds regardless of threshold status

---

### Requirement: DSA Configuration
The system SHALL expose configuration parameters to control Delta-Summary Accumulation behavior.

#### Scenario: DSA disabled
- **GIVEN** `DSA_ENABLED` is set to `False`
- **WHEN** an incremental update occurs
- **THEN** the system falls back to full summary regeneration (existing behavior)

#### Scenario: Custom thresholds
- **GIVEN** custom values for `DSA_DELTA_COUNT_THRESHOLD` and `DSA_DELTA_TOKEN_THRESHOLD`
- **WHEN** compaction eligibility is evaluated
- **THEN** the custom thresholds are used instead of defaults

---

### Requirement: Delta Cleanup on Community Restructure
The system SHALL handle orphan delta summaries when community structure changes due to Leiden re-detection.

#### Scenario: Community deleted during re-detection
- **GIVEN** a community with pending deltas
- **WHEN** Leiden re-detection removes or merges this community
- **THEN** the associated delta nodes are deleted or marked as orphaned
- **AND** no errors occur during subsequent queries
