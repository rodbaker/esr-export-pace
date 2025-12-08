# ESR Project Specialized Agents

This directory contains specialized Claude agents for the ESR Export Pace Analysis project. Each agent is an expert in a specific domain and can be invoked to assist with related tasks.

## Available Agents

### 🌾 Agricultural Domain Expert
**File**: `agricultural-domain-expert.md`

**Expertise**:
- Marketing year cycles and agricultural calendars
- Export pace analysis methodologies
- USDA terminology and reporting standards
- Wheat commodity classifications
- Seasonal export patterns
- Stakeholder perspectives (USDA, traders, farmers)

**Use When**:
- Interpreting export performance data
- Understanding marketing year calculations
- Explaining agricultural business concepts
- Reviewing analysis for domain accuracy
- Writing reports for agricultural audiences

**Example Questions**:
- "Why are MY 2026 exports starting June 1, 2025?"
- "What's a normal pace deviation in Q1 vs Q3?"
- "How do outstanding sales predict future shipments?"
- "Is this seasonal pattern typical for wheat exports?"

---

### 🔧 Technical Specialist
**File**: `technical-specialist.md`

**Expertise**:
- SQLite compatibility and data type handling
- USDA ESR API authentication and patterns
- Pandas and NumPy optimization
- Plotly visualization techniques
- Database query optimization
- Error handling and debugging

**Use When**:
- Debugging SQLite type errors
- Implementing API integrations
- Optimizing database queries
- Fixing data pipeline issues
- Resolving technical gotchas

**Example Questions**:
- "Why is SQLite rejecting my numpy.int64 values?"
- "How do I authenticate with the USDA API?"
- "What's the correct pattern for cleaning data before database save?"
- "How should I calculate marketing weeks?"

---

### 🏗️ Code Architect
**File**: `code-architect.md`

**Expertise**:
- System architecture and design patterns
- Code organization and module structure
- Dependency management
- Extension points and scalability
- Performance optimization
- Design decisions and trade-offs

**Use When**:
- Planning new features or refactoring
- Understanding codebase structure
- Making architectural decisions
- Reviewing code for pattern consistency
- Extending system capabilities

**Example Questions**:
- "Where should I add support for a new commodity?"
- "What's the data flow from API to visualization?"
- "Why did we choose SQLite over PostgreSQL?"
- "How do I add a new validation rule?"

---

### ✅ Validation & Business Logic Expert
**File**: `validation-expert.md`

**Expertise**:
- Data quality validation rules
- Business logic enforcement
- Validation severity levels
- Common validation failures
- Data integrity requirements
- Export metrics definitions

**Use When**:
- Adding new validation rules
- Debugging validation failures
- Understanding business rules
- Ensuring data quality
- Interpreting validation reports

**Example Questions**:
- "Why did my data fail the accumulation check?"
- "What severity should I use for this validation?"
- "How do I validate marketing year boundaries?"
- "What's the difference between accumulated exports and total commitment?"

## How to Use Agents

### Method 1: Direct Reference (Recommended)
When working on a task, reference the relevant agent file directly:

```
I'm implementing a new commodity. Let me check the Code Architect agent...

[Read .claude/agents/code-architect.md]

Based on the extension points section, I should:
1. Add metadata to config/commodities.yaml
2. Run fetch_historical_data.py
3. No code changes needed
```

### Method 2: Invoke via Claude Code
If you have access to Claude Code's agent system, you can invoke agents by name:

```
/agent agricultural-domain-expert
"Explain why wheat exports peak in Q2"
```

### Method 3: Multi-Agent Collaboration
For complex tasks, consult multiple agents:

```
Task: Add validation for seasonal export patterns

1. Agricultural Domain Expert: What are normal seasonal patterns?
2. Validation Expert: How should I structure this validation rule?
3. Code Architect: Where in the codebase does this belong?
4. Technical Specialist: How do I implement the statistical check?
```

## Agent File Format

Each agent file follows this structure:

```markdown
# [Agent Name]

You are the [Role] for the ESR project...

## Core Domain Knowledge
- Key concepts
- Important patterns
- Business rules

## [Category 1]
### Detailed information...

## [Category 2]
### More details...

## Key Files to Reference
- Links to relevant code

## Response Guidelines
- How the agent should respond
```

## Quick Reference

| Domain | Agent | Primary Focus |
|--------|-------|---------------|
| **Business** | Agricultural Domain Expert | Marketing years, pace analysis, USDA standards |
| **Technical** | Technical Specialist | SQLite, API, data types, debugging |
| **Architecture** | Code Architect | Design patterns, structure, extensibility |
| **Quality** | Validation Expert | Data validation, business rules, metrics |

## Creating New Agents

To add a new specialized agent:

1. Create `[agent-name].md` in this directory
2. Follow the standard agent file format
3. Define clear expertise boundaries
4. Include practical examples and code patterns
5. Reference specific files and line numbers
6. Add to this README

## Integration with Subagent Guidelines

These agents complement the project's subagent guidelines (`docs/claude/subagent_guidelines.md`):

- **Subagent Guidelines**: How to onboard and work with subagents
- **Agent Files**: Specialized knowledge bases for specific domains

Use subagent guidelines for process, use agent files for domain expertise.

## Maintenance

Keep agent files updated when:
- ✅ New features are added
- ✅ Technical patterns change
- ✅ Business rules evolve
- ✅ Common issues are discovered
- ✅ Architecture decisions are made

Last Updated: 2025-12-06
