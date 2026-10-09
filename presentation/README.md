# Presentation for the current demo

Open **[demo-ready/Nellai_Green_Civic_Demo_Ready.pptx](demo-ready/Nellai_Green_Civic_Demo_Ready.pptx)**.
The matching PDF is a backup for viewing or printing. The deck has 23 editable
slides with speaker notes, architecture/workflow diagrams, fresh screenshots,
email-outbox demonstration and verified test results. The cover includes the
provided details: **Santhiya M**, **952825405014**, **M.E. CSE — Final Year**, and
**SCAD College of Engineering & Technology**, with the supplied college logo.
The original logo is kept in `assets/scad-college-logo.png` for regeneration.

The earlier `Nellai_Green_Civic_ME_Demo.pptx` and PDF remain on the original PC.
The upload ZIP includes the updated `demo-ready` deck and PDF to avoid mixing versions.

Gmail accepted the test complaint **NGC-063524AD** for `sandymuthukutti@gmail.com`
on 7 October 2026. The updated screenshot shows the real `SENT` state. This proves
SMTP acceptance; Inbox/Spam receipt must be checked separately. A newly extracted
copy requires private Gmail setup and generates fresh demo records. The slides
identify AI classification as future work rather than a completed trained model.

The rehearsal script, sample complaint, role-switching sequence and viva answers
are in **[../docs/demo-guide.md](../docs/demo-guide.md)**.

To regenerate the new deck after capturing screenshots:

```bash
.venv/bin/python scripts/create_presentation.py
libreoffice --headless --convert-to pdf --outdir presentation/demo-ready presentation/demo-ready/Nellai_Green_Civic_Demo_Ready.pptx
```
