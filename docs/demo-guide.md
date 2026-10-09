# ME project live demonstration

## Before presenting

1. On the original PC run `bash start.sh`. On another PC first follow `RUN_ON_ANOTHER_PC.md` and use its Windows, Linux or macOS launcher.
2. Open http://localhost:8080 and check http://localhost:8080/health.
3. Open `runtime/DEMO_CREDENTIALS.md` privately. Do not show passwords on presentation slides.
4. Prepare one actual, non-sensitive JPEG/PNG to demonstrate upload. Sample evidence cards are explicitly illustrative.
5. Use separate browser profiles (normal/incognito) for citizen and staff, or sign out between roles.
6. Open `presentation/demo-ready/Nellai_Green_Civic_Demo_Ready.pptx`. The matching PDF is your backup. The cover includes Santhiya M, register number 952825405014, M.E. CSE — Final Year, and the supplied SCAD College of Engineering & Technology logo.

## Suggested 8–10 minute demo

| Time | Action | Point to explain |
|---|---|---|
| 0:00–1:00 | Sign in as citizen; show overview | One place for civic reporting and environmental participation. Seeded records are demonstration data. |
| 1:00–2:30 | Report issue with photo; category Drain Blockage; location 8.7200, 77.7410 | GPS/manual coordinates, validation, private images, generated complaint reference. |
| 2:30–3:30 | Show assigned team and deadline | Category + configured boundary + responsibility rule; weekends and configured holidays are excluded. |
| Email highlight | Sign in as administrator → Authority email outbox → choose your report | The recipient is sandymuthukutti@gmail.com. Allow about 30 seconds for the worker; SENT means SMTP acceptance. Show the actual Inbox/Spam message only if it is present. A new PC requires private Gmail setup first. |
| 3:30–5:00 | Sign in as authority; acknowledge → start work → submit resolution photo | The API enforces permitted transitions and the assigned team's permissions. |
| 5:00–6:00 | Return to the same citizen account; verify resolution | Citizen can close or reopen. An administrator cannot impersonate citizen verification. |
| 6:00–7:00 | Open environmental map and switch layers | PostGIS stores spatial data; Leaflet shows clusters, heatmap, trees and water. Public locations are approximate. |
| 7:00–8:00 | Register/join as a volunteer; register a tree | Participation and tree survival are separate optional modules. |
| 8:00–9:00 | Sign in as administrator; open Administration | Show responsibility rules, calendars and due escalation action. |
| 9:00–10:00 | Enable Flood monitoring in Module registry | New module appears in navigation. Its manually entered gauge readings do not claim live sensor data or flood forecasts. |

## Escalation without waiting three working days

The seed includes one overdue demonstration complaint. “Run due escalations” processes only actually overdue records and is safe to repeat. The background worker may have already processed that record before your presentation; show the complaint timeline and escalation level in that case. No hidden accelerated clock or fake government notification is used.

For an entirely fresh presentation dataset, use a separate new database and rerun setup. Do not reset or overwrite a database containing records you want to retain.

## Useful explanations for the viva

- **Why PostGIS?** Indexed distance and polygon operations support nearby reports and jurisdiction lookup.
- **Why modular?** Green, volunteer, water and flood extensions can be disabled while the core complaint engine remains usable.
- **Why citizen verification?** Staff submission of evidence is not proof that the citizen accepts the result; the workflow records both.
- **Why no automatic duplicate deletion?** Similar reports can contain distinct evidence. An administrator links them after review and retains the original.
- **What does AI do now?** There is a versioned, tested provider contract with no loaded model. Classification is currently human supplied.
- **Has Gmail received the complaint?** Gmail's SMTP server accepted test NGC-063524AD on 7 October 2026 and the outbox records SENT. This is evidence of server acceptance; inbox arrival is checked separately. Automatic alerts are enabled on the original PC. Configure a sending account privately when installing on another PC.
- **What happens if email fails?** The report remains saved. The worker retries the alert with increasing delays, records the attempt count, and marks it failed after five unsuccessful attempts.
- **Is this a government system?** No. The demo uses synthetic authorities/boundaries and has no official integration.
- **Is it real time?** APIs persist real changes. Browser pages refresh every 15 seconds and the worker checks email alerts and deadlines every 30 seconds. This is polling, not a streaming sensor system.
- **Can it run on another PC?** The ZIP includes Windows, Linux and macOS launchers and the built website. Python 3.12 and internet are needed for first setup. SQLite avoids requiring Docker for the portable demo; PostgreSQL/PostGIS remains the original spatial deployment.
- **What is future work?** Trained models, verified official data, native mobile apps, push delivery, larger-scale tests, privacy review and production operations.

## Ready-made complaint for the demonstration

- Title: `Demo: blocked drain near the bus stop`
- Description: `DEMONSTRATION ONLY: Waste is blocking the roadside drain near the bus stop. Please assign the maintenance team to inspect and clear the drain. This is sample data for the project presentation.`
- Category: `Drain Blockage`
- Locality: `Palayamkottai (demo)`
- Latitude: `8.7200`; longitude: `77.7410`
- Photograph: choose `tests/fixtures/evidence.png` as labelled example evidence.
- Authority resolution: `DEMONSTRATION ONLY: The maintenance team removed the obstruction and checked water flow. This is sample resolution evidence for the project presentation.`
- Citizen verification: `I confirm the demonstration workflow is complete.`

For the already prepared email example, open complaint `NGC-063524AD` in the
administrator outbox. It is explicitly marked as a test and needs no field action.
This reference belongs to the original PC. On a fresh installation submit a new
complaint and use its generated reference instead.

## Short speaking script

“Good morning. I am Santhiya M, register number 952825405014, a final-year M.E.
Computer Science and Engineering student at SCAD College of Engineering & Technology.
My project is Nellai Green & Civic, a web platform for managing civic complaints
and community environmental activities. A citizen submits a report with a photo
and location. The system assigns a configured team, sets a working-day deadline,
and automatically creates an authority email alert. Staff record progress and
resolution evidence. The original citizen confirms the result or reopens it.
For this localhost demonstration, the worker sends authority alerts through Gmail
and the admin outbox records their status. A real test was accepted by Gmail's mail
server; the recipient checks Inbox or Spam to confirm arrival. AI classification is
a planned extension, while the complaint workflow shown here is implemented.”

## Speaking notes for each demonstration stage

1. **Problem:** “Residents need a clear way to report local maintenance problems,
   know which team is responsible and check what action was taken. This prototype
   brings those steps into one application.”
2. **Submission:** “I am signed in as a citizen. I enter a title, description,
   category, photograph and location. A sensor is not required: location can be
   entered manually. This example is clearly labelled as demonstration data.”
3. **Assignment:** “The system uses configured category and boundary rules to
   assign a team. It calculates a deadline using the working calendar. These are
   illustrative teams and boundaries, not an official government integration.”
4. **Email:** “The complaint and email queue entry are saved together. A separate
   worker sends the email so the form does not wait for Gmail. The message contains
   the reference, problem description, location, team and a private review link.
   Pending means waiting; sent means the mail server accepted it.”
5. **Staff action:** “The assigned authority acknowledges the report, starts work
   and uploads resolution evidence. Each step appears in the complaint history.”
6. **Citizen control:** “The original citizen verifies the solution or reopens the
   issue. The officer cannot complete this verification on the citizen's behalf.”
7. **Related modules:** “The same platform provides tree care records, volunteer
   activities and water observations. The optional flood module takes manual
   readings. It does not claim sensor feeds or flood predictions.”
8. **Engineering and results:** “The backend uses FastAPI, the interface uses
   React, and the original database uses PostgreSQL/PostGIS. The portable package
   uses SQLite. Twenty-five backend/module tests passed on PostGIS, and the three
   browser scenarios verify the workflow, outbox and application screens.”
9. **Closing:** “The implemented result is a working complaint lifecycle with
   automatic authority emails and citizen verification. Trained AI classification,
   verified government integration and a completed native mobile app are future
   extensions.”

## Rehearsal checklist

- Extract and run the ZIP on the actual presentation PC before the demo.
- Confirm all three logins work using that PC's generated credentials.
- If demonstrating real email, configure Gmail on that PC and submit a labelled
  test ahead of time; check Inbox/Spam and the outbox state.
- Keep the PPT and PDF open, and keep credentials and App Passwords off screen.
- Explain the recorded original Gmail test honestly if internet or mail login is
  unavailable. Continue the local complaint workflow and show the pending outbox.

If the live app is unavailable during the presentation, use the screenshot slides
and PDF. The basemap requires internet; complaint forms and the local email preview
do not. The slides contain speaker notes with explanations and limitations.
