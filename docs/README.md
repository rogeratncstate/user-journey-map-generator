# Course collateral directory

Place the source material for each course in a subfolder within this directory. The
subfolder name should match the course folder you want to create in GitHub.

For example, to generate personas for `Introduction_to_Data_Science`, create the
following structure:

```
docs/
└── Introduction_to_Data_Science/
    ├── feasibility_assessment.md
    ├── course_design_notes.md
    └── lightcast_industry_summary.txt
```

The generator currently ingests `.md`, `.txt`, and `.json` files. Convert PDF or
presentation decks to text before running the automation.
