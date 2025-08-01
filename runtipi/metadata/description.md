# GLPI Matrix Notifier

This application monitors new tickets on a GLPI instance and forwards a message to a Matrix room.

Place this repository under `/opt/runtipi/apps/glpi-matrix-notifier`, copy the
files from the `runtipi` directory to the app folder, and run
`./runtipi-cli app install glpi-matrix-notifier` from `/opt/runtipi` to deploy.
After installation, configure the environment variables from Tipi's interface
(Apps → Manage) or by editing `config.json`.
