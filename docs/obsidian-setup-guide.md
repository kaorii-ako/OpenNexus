# Obsidian Setup Guide: Agentic OS + Student Life OS
**For:** Tawin Tangsukson — Developer + Student, Bangkok  
**Date:** 2026-06-01

---

## What This Is

Two systems running in one vault:

- **Agentic OS** — Your dev brain. Projects, code research, system designs, technical decisions, build logs. Everything you build lives here.
- **Student Life OS** — Your academic brain. Courses, assignments, exams, deadlines, study notes, ideas.

They share the same vault. They don't collide. NEXUS indexes both and knows the difference via tags and folder structure.

---

## Vault Structure

```
NEXUSVault/
│
├── 00 - Inbox/               ← dump zone, process daily
│
├── 10 - Daily Notes/         ← NEXUS auto-creates these
│   ├── 2026-06-01.md
│   └── Templates/
│       └── Daily Note.md
│
├── 20 - Projects/            ← Agentic OS: dev projects
│   ├── NEXUS/
│   ├── OpenNexus/
│   └── Templates/
│       └── Project.md
│
├── 30 - Research/            ← deep dives, technical docs
│   ├── AI/
│   ├── Systems/
│   └── Templates/
│       └── Research.md
│
├── 40 - Courses/             ← Student Life OS: every class
│   ├── CS101/
│   │   ├── Lectures/
│   │   ├── Assignments/
│   │   └── Exams/
│   └── Templates/
│       ├── Lecture.md
│       ├── Assignment.md
│       └── Exam Prep.md
│
├── 50 - Ideas/               ← raw captures, unprocessed
│
├── 60 - People/              ← professors, teammates, mentors
│   └── Templates/
│       └── Person.md
│
├── 70 - Resources/           ← articles saved, reference docs
│
├── 80 - Areas/               ← ongoing responsibilities (health, finances, career)
│   ├── Career/
│   ├── Health/
│   └── Finances/
│
└── 90 - Archive/             ← done projects, old courses
```

---

## Recommended Obsidian Plugins

Install via Settings → Community Plugins:

| Plugin | Why |
|---|---|
| **Templater** | Smart templates with dynamic dates, NEXUS hooks |
| **Dataview** | Query your notes like a database |
| **Calendar** | Daily note navigation, visual week view |
| **Tasks** | Cross-vault task tracking with due dates |
| **Tag Wrangler** | Rename/merge tags without breaking links |
| **Minimal Theme** | Cleanest reading experience |
| **Style Settings** | Customize Minimal theme colors |

Optional but powerful:
| Plugin | Why |
|---|---|
| **Excalidraw** | Diagrams and system designs inside notes |
| **Kanban** | Project board view from markdown |
| **Advanced Tables** | Better table editing |

---

## Tag System

Everything is tagged. NEXUS uses tags for routing and retrieval.

### Status Tags
```
#status/active      currently working on it
#status/waiting     blocked on someone/something
#status/done        completed
#status/dropped     not doing this anymore
#status/someday     future idea
```

### Type Tags
```
#type/project       dev project note
#type/course        academic course
#type/lecture       lecture note
#type/assignment    homework / lab
#type/exam          exam prep
#type/research      deep technical research
#type/idea          unprocessed idea
#type/person        someone I know
#type/resource      reference material
```

### Domain Tags
```
#domain/ai          AI / ML / LLM
#domain/backend     APIs, databases, systems
#domain/frontend    UI, React, CSS
#domain/devops      deployment, infrastructure
#domain/cs          computer science fundamentals
#domain/math        mathematics for CS
```

### Priority Tags (for Tasks plugin)
```
#p1    must do today
#p2    this week
#p3    this month
#p4    someday
```

---

## The Agentic OS Workflow

### Starting a New Project

1. Create folder: `20 - Projects/[project-name]/`
2. Create `20 - Projects/[project-name]/README.md` from Project template
3. Run `nexus note "Starting [project-name]: [one-line goal]"` — NEXUS captures it

**Project template structure:**
```markdown
---
tags: [type/project, status/active, domain/backend]
created: {{date}}
status: active
---

# [Project Name]

## Goal
One sentence. What does this do and why does it matter?

## Context
Why am I building this? What problem does it solve?

## Architecture
High-level system design. Link to research notes.

## Build Log
### {{date}}
- Started project

## Decisions
| Decision | Options Considered | Chosen | Why |
|---|---|---|---|

## Open Questions
- [ ] 

## Resources
- 

## Status
- [ ] MVP defined
- [ ] First working version
- [ ] Deployed / shared
```

### Daily Dev Workflow

**Morning (when NEXUS digest runs at 08:00):**
- Read digest in terminal or open NEXUS dashboard → Digest view
- Check `## Top 3 Priorities` in today's daily note
- Pick what you're building

**During work:**
- `nexus log "built X, blocked on Y"` → appends to daily note
- `nexus note "idea for Z"` → drops into 50 - Ideas/
- Use `[[wikilinks]]` heavily — link your code decisions to research notes

**End of day:**
- Fill `## End of Day Reflection` in daily note (30 seconds)
- Move done tasks in Projects to `## Build Log`
- Tag anything in Inbox

### Weekly Review (Sunday, 20 min)

1. Open Dataview query (see §Dataview Queries) — all `#status/active` projects
2. Update status tags on stalled projects
3. Move completed projects to `90 - Archive/`
4. Review Ideas folder — promote anything worth pursuing

---

## The Student Life OS Workflow

### Setting Up a New Course

1. Create folder: `40 - Courses/[COURSE-CODE]/`
2. Create subfolders: `Lectures/`, `Assignments/`, `Exams/`
3. Create `40 - Courses/[COURSE-CODE]/Overview.md` with syllabus, professor, schedule

**Course Overview template:**
```markdown
---
tags: [type/course, status/active]
course_code: CS101
professor: "Prof. [Name]"
semester: "2026-S1"
credits: 3
exam_date: 2026-07-15
---

# [Course Name]

## Description
What this course covers.

## Schedule
Lectures: Mon/Wed 09:00–10:30

## Grading
- Midterm: 30%
- Final: 40%
- Assignments: 30%

## Key Dates
| Date | Event |
|---|---|
| 2026-07-15 | Final exam |

## Resources
- Textbook:
- Slides folder:
```

### Lecture Note System

Filename: `YYYY-MM-DD [Topic].md` inside `40 - Courses/[COURSE]/Lectures/`

**Lecture template:**
```markdown
---
tags: [type/lecture, domain/cs]
course: "[[CS101 Overview]]"
date: {{date}}
topic: 
---

# {{date}} — [Topic]

## Key Concepts
- 

## Notes
[your notes here]

## Questions I Had
- 

## Follow Up
- [ ] Read chapter X
- [ ] Understand Y better

## Summary (one paragraph)
```

### Assignment Tracking

Filename: `[COURSE]-HW[N]-[Topic].md` inside `40 - Courses/[COURSE]/Assignments/`

```markdown
---
tags: [type/assignment, status/active, #p1]
course: "[[CS101 Overview]]"
due: 2026-06-15
submitted: false
grade: 
---

# HW3 — [Topic]

## Requirements
- [ ] Task 1
- [ ] Task 2

## My Approach

## Code / Solution

## Submission
- [ ] Submitted on [date]
```

Use Tasks plugin to see ALL assignments across ALL courses in one view.

### Exam Prep System

Create one note per exam: `FINAL-CS101-2026-07-15.md`

```markdown
---
tags: [type/exam, status/active, #p1]
course: "[[CS101 Overview]]"
exam_date: 2026-07-15
---

# CS101 Final Exam Prep

## Topics to Cover
- [ ] Chapter 1: [topic] — confidence: low/medium/high
- [ ] Chapter 2: [topic] — confidence: medium

## Key Formulas / Concepts
| Concept | Formula/Rule | Status |
|---|---|---|

## Practice Problems Done
- [ ] Past paper 2024

## Notes by Topic
### Topic 1
...
```

---

## Dataview Queries

Add these to a `Dashboard.md` note in your vault root.

### Active Projects
```dataview
TABLE status, tags
FROM "20 - Projects"
WHERE contains(tags, "status/active")
SORT file.mtime DESC
```

### Upcoming Deadlines
```dataview
TABLE due, course, submitted
FROM "40 - Courses"
WHERE type = "assignment" AND submitted = false
SORT due ASC
```

### All Open Tasks
```tasks
not done
tags include #p1
```

### Ideas Not Processed
```dataview
LIST
FROM "50 - Ideas"
SORT file.ctime DESC
LIMIT 20
```

### Today's Notes
```dataview
LIST
WHERE file.cday = date(today)
SORT file.mtime DESC
```

---

## NEXUS Integration Points

Once NEXUS is running, it connects to your vault at a deeper level:

| NEXUS Command | What It Does to Vault |
|---|---|
| `nexus digest` | Writes briefing to today's daily note `## Morning Briefing` |
| `nexus log "..."` | Appends to today's `## Notes` section |
| `nexus note "..."` | Creates new file in `50 - Ideas/` with timestamp |
| `nexus memory index` | Indexes entire vault into ChromaDB for RAG |
| `nexus ask "..."` | Retrieves top 5 vault chunks relevant to query |
| `nexus chat` | Full conversation with vault as memory |

NEXUS reads your course notes and can answer questions about your classes. It reads your project logs and understands what you're building. Ask it things like:

- `nexus ask "what was I stuck on last Tuesday?"`
- `nexus ask "summarize my CS101 notes on recursion"`
- `nexus ask "what open PRs need my attention?"`
- `nexus ask "what should I work on today?"`

---

## Daily Note Template

NEXUS auto-creates this each morning:

```markdown
---
date: {{date}}
tags: [type/daily]
week: {{week_number}}
---

# {{date}}

## Morning Briefing
<!-- NEXUS fills this at 08:00 -->

## Schedule
<!-- Calendar events pulled by NEXUS -->

## Top 3 Priorities
- [ ] 
- [ ] 
- [ ] 

## Notes
<!-- nexus log appends here -->

## Ideas
<!-- nexus note captures here -->

## End of Day Reflection
**What shipped:**

**Blockers:**

**Tomorrow:**
```

---

## Getting Started Checklist

- [ ] Install Obsidian (free, obsidian.md)
- [ ] Run `nexus serve` and let it scaffold the vault
- [ ] Install recommended plugins (Templater, Dataview, Calendar, Tasks)
- [ ] Set Templater template folder to `Daily Notes/Templates`
- [ ] Set new daily note location to `Daily Notes/`
- [ ] Set daily note template to `Daily Notes/Templates/Daily Note.md`
- [ ] Create your first course folder in `40 - Courses/`
- [ ] Create `Dashboard.md` with Dataview queries
- [ ] Run `nexus memory index` to index the vault

---

## Tips

**Link everything.** `[[CS101 Overview]]` in your project note, `[[NEXUS]]` in your research notes. Obsidian graph view becomes useful only when you link.

**Process Inbox daily.** The inbox is temporary. Move notes to correct folders, add tags, add links. 5 minutes a day beats 2 hours on Sunday.

**Use NEXUS as your memory.** You don't need to remember what you read. Write it down, let NEXUS index it, ask later.

**One daily note per day, always.** Even if you only write one line. It compounds.

**Don't over-organize up front.** Add structure as you need it. Start with just Projects and Courses. The rest emerges.
