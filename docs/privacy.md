# Local demonstration privacy information

This installation is an ME project demonstration. Use fictional accounts and non-sensitive demonstration images. It is not connected to official government complaint systems.

## What the software stores

Account name and contact identifier; a password hash; sign-in sessions; complaint title, description, coordinates and submitted photograph; staff workflow updates; resolution evidence; notifications; volunteer profile and activity participation; environmental records and audit history.

## Who can see it

Citizens can see their own detailed complaints. Assigned authority users can see their team's complaints. Administrators can manage complaints and platform settings. Public map views show category/status and approximate locations, without reporter contact details or photographs. Volunteer profiles are visible to administrators, not exposed as public personal-location markers.

## Photos and permissions

The browser requests location only after you select “Use my current location”. You can enter coordinates manually. Photos are selected using the device's file picker. The backend re-encodes images and strips EXIF metadata. Avoid recognizable people, private addresses, documents and sensitive locations.

OpenStreetMap serves external map tiles; map requests send network information to that service. Optional Google Fonts requests are used by the web styling; local system fonts are the fallback. These external requests should be reviewed or self-hosted for a public deployment.

## Deletion and retention

Use **My account → Delete my account** and enter your password. Citizen account deletion revokes access, removes contact details and original complaint photo/text, and anonymizes report ownership. Some operational history and environmental records remain. Staff accounts must transfer responsibilities before deletion. The local database and uploads persist until the operator deletes or replaces them. No automatic retention purge is claimed.

For this local demo, ask the presenter/operator to remove additional test data. Before a public deployment, replace this document with the operator's legal identity, contact address, retention schedule, lawful basis/consent process, complaint process and complete data-deletion route. This template is not a completed legal review.
