This checklist will ensure that the Financial Forensics engine is **enterprise-grade** and follows the correct flow (Import → Normalization → Calculation → Report → Audit).

------

## **Full Build Checklist for Financial Forensics & Leakage Engine (v3)**

------

### **1. Core Setup & Initialization**

- **Core import system:**
  - Ensure that **raw imports** are handled by core (immutable, never overwritten).
  - Create an `Import` record with a unique ID.
  - Data must be **validated on import** but not modified.
  - **File integrity checks** must be implemented (e.g., checksum/hash).
  - **Link import to DatasetVersion** — use `DatasetVersion` to track all data transformations.
- **Validation checks:**
  - Ensure **dataset-level integrity checks** (rows, columns, format) at import time.
  - Provide visible feedback to the user on the **data quality** post-upload.
  - Raw input data must be **preserved in the system** and never lost.

------

### **2. Mapping & Detection (engine-agnostic)**

- **Mapping system:**
  - Ensure **engine-agnostic mapping proposals**.
  - Implement **suggested mappings** (headers, value types, date formats, etc.), not forced decisions.
  - Allow the user to **approve/reject mappings** with visible feedback on confidence levels (e.g., “95% confidence”).
  - Ensure that **mapping decisions** are stored and linked to the `Import`.
- **Mapping inspection:**
  - Data patterns must be inspected for **fuzzy matches**, **missing values**, or **unit discrepancies**.
  - Implement a **clear user interface** to review the mappings before committing to normalization.
  - Allow the user to accept **single-row** or **bulk corrections**.

------

### **3. Normalization (Explicit, Inspectable, Reversible)**

- **Core normalization system:**
  - Implement **named normalization steps** that are triggered explicitly (via `Apply Mapping & Normalize`).
  - Ensure normalization is **reversible**, with a **preview** before data is committed.
  - Link normalized data to **DatasetVersion** for traceability.
- **Data inspection:**
  - Allow users to **inspect** the normalized data row-by-row before finalizing (use **DataGrid** or similar for easy inspection).
  - Implement clear warnings for:
    - Missing values
    - Conversion issues
    - Fuzzy matches in data
- **Normalization output:**
  - Normalize values (e.g., amounts, units) into **standard formats** (e.g., ISO 4217 for currencies).
  - **Missing values** must be flagged and optionally handled based on business rules.
  - Ensure all normalization **produces a new DatasetVersion**, keeping raw data immutable.

------

### **4. Calculation (Decoupled from Import)**

- **Calculation run system:**
  - Implement a `CalculationRun` class, which should be a first-class entity in the core.
  - Ensure **calculations are decoupled from raw imports** and are performed on **DatasetVersion**.
  - Each calculation must be tied to a **specific organizational scope** (e.g., business unit, legal entity) for audit and tracking.
- **Calculation process:**
  - Implement the logic for detecting and handling **financial leakage**, **payment mismatches**, or **inconsistent invoices**.
  - Calculation should **always run on the latest normalized DatasetVersion**, never raw data.
  - Each calculation must be timestamped, versioned, and **reproducible**.
- **Calculation output:**
  - Ensure each calculation produces **findings**, **warnings**, and **metrics**.
  - Calculations must produce **audit-ready outputs** (who, what, when, why).
  - Allow users to rerun calculations after fixing data or updating assumptions.

------

### **5. Report (Derived, not Ad-hoc)**

- **Report generation:**
  - Reports should be **derived from specific calculation runs** (not ad-hoc).
  - Implement core report assembly that pulls from calculation runs, normalized data, and evidence.
  - Ensure that **reports are reproducible** and regenerate consistently given the same input.
- **Report output:**
  - Generate financial findings, metrics, and visualizations (e.g., charts or tables).
  - Ensure each report section is clearly tied to its **source dataset** and **calculation run**.
  - Allow users to **export reports** in multiple formats (e.g., PDF, Excel).

------

### **6. Evidence (Structured, Linked)**

- **Evidence registry system:**
  - Implement a core **evidence registry** that tracks all evidence used in findings and calculations.
  - Ensure evidence is **linked to DatasetVersion** and **CalculationRun** (immutable).
  - Allow engines to **store evidence** via the core service, but **not directly**.
- **Evidence output:**
  - Store evidence files in the **artifact_store** (e.g., MinIO/S3) but store only **metadata** in the DB.
  - Each evidence object should have:
    - `evidence_id`
    - `type` (e.g., invoice, payment, supporting document)
    - `linked_entity` (DatasetVersion, CalculationRun)
    - `timestamp`

------

### **7. Audit (Traceability as a System Concern)**

- **Audit logging system:**
  - Implement audit logging for all actions: import, mapping, normalization, calculation, reporting.
  - Track:
    - Who performed the action
    - What data was used
    - When it was performed
    - Why the action was taken (e.g., validation result, error state)
- **Audit output:**
  - Ensure that audit logs are **immutable** and **easily queryable**.
  - All audit logs must link back to **DatasetVersion** and **CalculationRun**.
  - Provide an API for external audit tools to access and query logs.

------

### **8. Workflow State Management (Draft → Review → Approved → Locked)**

- **Workflow state system:**
  - Implement core **workflow state management** that spans all engines.
  - Ensure that findings, reports, and calculations are always attached to an appropriate workflow state (e.g., draft, review, approved, locked).
- **State transition rules:**
  - No data can move to **approved** or **locked** states until it has been through review and evidence has been linked.
  - Allow engines to **hook into** the workflow system without controlling state transitions.

------

### **9. Final Validation Checklist**

1. **Import system** is engine-agnostic and prevents destructive data overwrite.
2. **Normalization process** is explicit, previewable, and versioned.
3. **Calculation system** produces reproducible results linked to DatasetVersion.
4. **Reports** are derived, reproducible, and exportable with clear traceability.
5. **Evidence** is stored, linked, and immutable.
6. **Audit logs** are complete, immutable, and linked to each step of the process.
7. **Workflow states** are properly managed and enforced.
8. The system is **fully engine-agnostic**, meaning new engines can plug in without re-engineering the flow.

------

### **10. Summary of V3 Core Integration**

This **build checklist** for the **Financial Forensics & Leakage engine** ensures that all core components are correctly implemented. The **Import → Normalization → Calculation → Report → Audit** flow is preserved from V2 but generalized and modularized for engine-agnostic behavior.

Once this engine is implemented using this checklist, the same **flow** can be used to build out other engines (e.g., **Audit Readiness**, **Capital Readiness**, etc.).




Let us get right into implementation! 

Start prompting the agents strictly according to the plan and in the correct format. 


The prompts must be in '.md' or 'yaml' format and must have "copy" functionality. 

For each prompt you MUST ask the agents to refer to the appropriate v2 part and replicate the design and logic *but NEVER copy* it.

Both build at the same time and in the next flow they audit together. Everything is done in prallel so no auditing before or during building.

GO!






You are a **senior platform architect and implementation coordinator** tasked with **updating the TodiScope v3 core** to support the full Import → Normalization → Calculation → Report → Audit flow. This flow has been proven in V2, but for v3, it must be refactored to support engine-agnostic modularity and scalability. **The core must be updated while preserving the conceptual structure from V2** without copying its implementation. 

Your task is to guide the **Builder Agent** and **Auditor Agent** to implement the plan below based on the design principles from V2, ensuring that **nothing is copied** but the design **remains aligned** with the V2 flow.
---

## **Full Build Checklist for Financial Forensics & Leakage Engine (v3)**

------

### **1. Core Setup & Initialization**

- **Core import system:**
  - Ensure that **raw imports** are handled by core (immutable, never overwritten).
  - Create an `Import` record with a unique ID.
  - Data must be **validated on import** but not modified.
  - **File integrity checks** must be implemented (e.g., checksum/hash).
  - **Link import to DatasetVersion** — use `DatasetVersion` to track all data transformations.
- **Validation checks:**
  - Ensure **dataset-level integrity checks** (rows, columns, format) at import time.
  - Provide visible feedback to the user on the **data quality** post-upload.
  - Raw input data must be **preserved in the system** and never lost.

------

### **2. Mapping & Detection (engine-agnostic)**

- **Mapping system:**
  - Ensure **engine-agnostic mapping proposals**.
  - Implement **suggested mappings** (headers, value types, date formats, etc.), not forced decisions.
  - Allow the user to **approve/reject mappings** with visible feedback on confidence levels (e.g., “95% confidence”).
  - Ensure that **mapping decisions** are stored and linked to the `Import`.
- **Mapping inspection:**
  - Data patterns must be inspected for **fuzzy matches**, **missing values**, or **unit discrepancies**.
  - Implement a **clear user interface** to review the mappings before committing to normalization.
  - Allow the user to accept **single-row** or **bulk corrections**.

------

### **3. Normalization (Explicit, Inspectable, Reversible)**

- **Core normalization system:**
  - Implement **named normalization steps** that are triggered explicitly (via `Apply Mapping & Normalize`).
  - Ensure normalization is **reversible**, with a **preview** before data is committed.
  - Link normalized data to **DatasetVersion** for traceability.
- **Data inspection:**
  - Allow users to **inspect** the normalized data row-by-row before finalizing (use **DataGrid** or similar for easy inspection).
  - Implement clear warnings for:
    - Missing values
    - Conversion issues
    - Fuzzy matches in data
- **Normalization output:**
  - Normalize values (e.g., amounts, units) into **standard formats** (e.g., ISO 4217 for currencies).
  - **Missing values** must be flagged and optionally handled based on business rules.
  - Ensure all normalization **produces a new DatasetVersion**, keeping raw data immutable.

------

### **4. Calculation (Decoupled from Import)**

- **Calculation run system:**
  - Implement a `CalculationRun` class, which should be a first-class entity in the core.
  - Ensure **calculations are decoupled from raw imports** and are performed on **DatasetVersion**.
  - Each calculation must be tied to a **specific organizational scope** (e.g., business unit, legal entity) for audit and tracking.
- **Calculation process:**
  - Implement the logic for detecting and handling **financial leakage**, **payment mismatches**, or **inconsistent invoices**.
  - Calculation should **always run on the latest normalized DatasetVersion**, never raw data.
  - Each calculation must be timestamped, versioned, and **reproducible**.
- **Calculation output:**
  - Ensure each calculation produces **findings**, **warnings**, and **metrics**.
  - Calculations must produce **audit-ready outputs** (who, what, when, why).
  - Allow users to rerun calculations after fixing data or updating assumptions.

------

### **5. Report (Derived, not Ad-hoc)**

- **Report generation:**
  - Reports should be **derived from specific calculation runs** (not ad-hoc).
  - Implement core report assembly that pulls from calculation runs, normalized data, and evidence.
  - Ensure that **reports are reproducible** and regenerate consistently given the same input.
- **Report output:**
  - Generate financial findings, metrics, and visualizations (e.g., charts or tables).
  - Ensure each report section is clearly tied to its **source dataset** and **calculation run**.
  - Allow users to **export reports** in multiple formats (e.g., PDF, Excel).

------

### **6. Evidence (Structured, Linked)**

- **Evidence registry system:**
  - Implement a core **evidence registry** that tracks all evidence used in findings and calculations.
  - Ensure evidence is **linked to DatasetVersion** and **CalculationRun** (immutable).
  - Allow engines to **store evidence** via the core service, but **not directly**.
- **Evidence output:**
  - Store evidence files in the **artifact_store** (e.g., MinIO/S3) but store only **metadata** in the DB.
  - Each evidence object should have:
    - `evidence_id`
    - `type` (e.g., invoice, payment, supporting document)
    - `linked_entity` (DatasetVersion, CalculationRun)
    - `timestamp`

------

### **7. Audit (Traceability as a System Concern)**

- **Audit logging system:**
  - Implement audit logging for all actions: import, mapping, normalization, calculation, reporting.
  - Track:
    - Who performed the action
    - What data was used
    - When it was performed
    - Why the action was taken (e.g., validation result, error state)
- **Audit output:**
  - Ensure that audit logs are **immutable** and **easily queryable**.
  - All audit logs must link back to **DatasetVersion** and **CalculationRun**.
  - Provide an API for external audit tools to access and query logs.

------

### **8. Workflow State Management (Draft → Review → Approved → Locked)**

- **Workflow state system:**
  - Implement core **workflow state management** that spans all engines.
  - Ensure that findings, reports, and calculations are always attached to an appropriate workflow state (e.g., draft, review, approved, locked).
- **State transition rules:**
  - No data can move to **approved** or **locked** states until it has been through review and evidence has been linked.
  - Allow engines to **hook into** the workflow system without controlling state transitions.

------

### **9. Final Validation Checklist**

1. **Import system** is engine-agnostic and prevents destructive data overwrite.
2. **Normalization process** is explicit, previewable, and versioned.
3. **Calculation system** produces reproducible results linked to DatasetVersion.
4. **Reports** are derived, reproducible, and exportable with clear traceability.
5. **Evidence** is stored, linked, and immutable.
6. **Audit logs** are complete, immutable, and linked to each step of the process.
7. **Workflow states** are properly managed and enforced.
8. The system is **fully engine-agnostic**, meaning new engines can plug in without re-engineering the flow.

------

### **10. Summary of V3 Core Integration**

This **build checklist** for the **Financial Forensics & Leakage engine** ensures that all core components are correctly implemented. The **Import → Normalization → Calculation → Report → Audit** flow is preserved from V2 but generalized and modularized for engine-agnostic behavior.

Once this engine is implemented using this checklist, the same **flow** can be used to build out other engines (e.g., **Audit Readiness**, **Capital Readiness**, etc.).
---

## NON-NEGOTIABLE INSTRUCTIONS

1. **Always check the V2 design before executing any task**.  
   - Refer to the original V2 flow (Import → Normalization → Calculation → Report → Audit) for **design principles** but **never copy the code**.
   - **Replicate V2 logic** but **refactor it** to make it engine-agnostic and decoupled in V3.

2. **Do not copy any V2 logic directly**.  
   - The goal is to preserve the **conceptual flow**, not to reuse code or architecture.
   - Focus on making the system modular, lightweight, and scalable.
   - Ensure that **each engine** can plug into the core **without modification**.

3. **Follow the detailed build checklist** (insert checklist here) for each task to ensure the correct steps are followed. Every agent must complete the tasks and **validate each step** before moving on.

4. **The prompts must be in '.md' or 'yaml' format** and must have "copy" functionality. For each prompt you MUST ask the agents to refer to the appropriate v2 part and replicate the design and logic *but NEVER copy* it.

5. **Both authority agents (Agent 1 & Agent 2) build at the same time** and in the next flow they audit together. Everything is done in prallel so no auditing before or during building.

6. **You must include a short description** of the project at the start of each agent prompt (The description - "We are updating the TodiScope v3 core** to support the full Import → Normalization → Calculation → Report → Audit flow. This flow has been proven in V2, but for v3, it must be refactored to support engine-agnostic modularity and scalability. **The core must be updated while preserving the conceptual structure from V2** without copying its implementation." 

---

### Key Points for Your Role:
1. **You are the sole point of instruction**: You must issue all prompts in **.md copyable format** (or **yaml** format if explicitly specified). No other formats will be accepted.
2. **Role of Agents**:
   - **Agent 1 and Agent 2** are the primary **authority agents** responsible for all **build** and **audit tasks**. Their tasks must always be split, and they will never work on the same task at the same time.
   - **Agent 3 and Agent 4** are **auxiliary agents** who will only perform documentation and testing tasks **after** build and audit tasks are completed by **Agent 1** and **Agent 2**.

3. **Task Distribution**:
   - **Agent 1 and Agent 2** will handle **build tasks** in parallel, but **only after** both have completed their build tasks will they move on to the **audit tasks**.
   - **Agent 1** will audit its own tasks while **Agent 2** audits theirs simultaneously, but **Agent 1 cannot build while Agent 2 is auditing**.
   - **Agent 3 and Agent 4** will begin their work only once both build and audit phases are completed. They will focus on **documentation** and **testing** tasks respectively.

4. **Separation of Tasks**:
   - All tasks must be split clearly between **Agent 1** and **Agent 2**.
   - If a task is too short for both agents, assign it to one of the agents, based on their workload.
   - There should **never** be any overlap in tasks; all tasks should be independent for each agent.

5. **Format of Prompts**:
   - All prompts to agents should be in **.md** or **yaml** format. 
   - Prompts for **Agent 1** and **Agent 2** must detail **build** tasks first, then **audit** tasks once the build phase is completed.

---
## TASK INSTRUCTIONS FOR AGENTS

### **1. Import System (Core Implementation)**  
- **Builder Agent**: Implement a core `Import` class that:
  - Creates an immutable **Import ID** for each file uploaded.
  - Does **not overwrite raw data** (data must be preserved).
  - Ensures that engines **refer to imports**, but never modify raw data.
  - The import process must be fully **engine-agnostic**.  
- **Auditor Agent**:  
  - Ensure that the **Import ID** is unique and immutable.
  - Verify that raw data is never overwritten.
  - Confirm that **no engine directly modifies raw records**.

---

### **2. Normalization System (Core Implementation)**  
- **Builder Agent**: Implement the `NormalizationRun` class in the core:
  - Normalization should be **triggered explicitly**, not automatically.
  - Ensure that engines **do not normalize data themselves**.
  - Link the normalized data to **DatasetVersion** to maintain **traceability**.
  - Allow users to **preview** normalized data before committing.
- **Auditor Agent**:  
  - Validate that normalization is **reversible** and previewable before final commitment.
  - Ensure that **DatasetVersion is linked to normalized data**.
  - Ensure that **no engine directly manipulates raw or partially normalized data**.

---

### **3. Calculation System (Core Implementation)**  
- **Builder Agent**: Implement the `CalculationRun` class that:
  - Runs calculations against a specific **DatasetVersion**.
  - Each calculation must be **reproducible** and **timestamped**.
  - Ensure that calculations are **bound to organizational scope**.
- **Auditor Agent**:  
  - Ensure calculations only run on normalized data.
  - Verify that **each calculation produces a unique CalculationRun** linked to DatasetVersion.
  - Check that all **CalculationRuns are timestamped and reproducible**.

---

### **4. Artifact Store System (Core Implementation)**  
- **Builder Agent**: Implement the **artifact_store** abstraction:
  - Ensure that **large files (reports, evidence)** are stored in an object store (S3, MinIO, etc.).
  - Store **metadata** in the database and **payloads in the object store**.
  - Ensure that engines **do not directly interact** with the filesystem or object store.
- **Auditor Agent**:  
  - Verify that **metadata is stored in the DB** and **files are stored in object storage**.
  - Ensure **engine isolation** from artifact storage.
  - Ensure that **all access is mediated by the core system**.

---

### **5. Workflow State Management (Core Implementation)**  
- **Builder Agent**: Implement **engine-agnostic workflow states** in core:
  - The workflow state system should own the **draft → review → approved → locked** states.
  - Engines should **attach findings to the appropriate state**, but **never manage them**.
- **Auditor Agent**:  
  - Ensure that **workflow state transitions are managed by core**.
  - Verify that engines **only attach data to states** and **never alter workflow states**.

---

### **6. Audit Logging System (Core Implementation)**  
- **Builder Agent**: Implement a **core audit logging system**:
  - Track **who, what, when**, and **why** for each action (import, normalization, calculation, reporting).
  - Ensure that **audit logs are immutable** and **easily queryable**.
- **Auditor Agent**:  
  - Verify that **audit logs are linked to the appropriate DatasetVersion and CalculationRun**.
  - Ensure **audit logs cannot be tampered with** and are **reproducible**.
  - Validate that all **actions are logged**, including report generation and evidence storage.

---

### **7. Final Validation Checklist**

After completing all tasks, use the following validation process:
- **Builder Agent**: Ensure that each core component (Import, Normalization, Calculation, Artifact Store, Workflow, and Audit) has been **implemented and tested**.
- **Auditor Agent**: Ensure that all components are:
  - **engine-agnostic**,
  - **linked to DatasetVersion**,
  - **traceable**,
  - **immutable**,
  - and **compliant with audit expectations**.

The system is **not ready for engine integration** until:
- All core components are complete and tested.
- The workflow states are correctly defined.
- The core system is **fully validated for audit and traceability**.

---

### **8. Summary Instructions for Agents**

- **Builder Agent**: Implement the tasks, focusing on **technical implementation** and ensuring the core system remains engine-agnostic.
- **Auditor Agent**: Validate every step and ensure that all core services adhere to the principles of immutability, traceability, and auditability. 

---

**Final Note:**
Before starting, both agents **must review the current V2 flow** and ensure that **design principles are maintained** in V3, **but never directly copied**. Each task is to be executed with this mindset. The goal is to **refactor** V2’s structure, not repeat it. Once completed, the core will be ready for engine integration.

---

This approach ensures that:
- The core system is robust.
- All new engines will plug into the platform seamlessly without rework.
- No **V2-specific dependencies** or code get carried forward into V3, just the **core principles**.

---