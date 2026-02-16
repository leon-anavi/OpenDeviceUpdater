#!/bin/bash
# Script to download/update local static assets
# Run from the project root directory

set -e

VERSION_VUE="3.4.15"
VERSION_VUETIFY="3.4.0"
VERSION_MDI="7.4.47"

echo "Downloading Vue.js $VERSION_VUE..."
curl -sL -o static/js/vue.global.prod.js "https://cdn.jsdelivr.net/npm/vue@${VERSION_VUE}/dist/vue.global.prod.js"

echo "Downloading Vuetify $VERSION_VUETIFY..."
curl -sL -o static/js/vuetify.min.js "https://cdn.jsdelivr.net/npm/vuetify@${VERSION_VUETIFY}/dist/vuetify.min.js"
curl -sL -o static/css/vuetify.min.css "https://cdn.jsdelivr.net/npm/vuetify@${VERSION_VUETIFY}/dist/vuetify.min.css"

echo "Downloading Material Design Icons $VERSION_MDI..."
curl -sL -o static/css/materialdesignicons.min.css "https://cdn.jsdelivr.net/npm/@mdi/font@${VERSION_MDI}/css/materialdesignicons.min.css"
curl -sL -o static/fonts/materialdesignicons-webfont.woff2 "https://cdn.jsdelivr.net/npm/@mdi/font@${VERSION_MDI}/fonts/materialdesignicons-webfont.woff2"
curl -sL -o static/fonts/materialdesignicons-webfont.woff "https://cdn.jsdelivr.net/npm/@mdi/font@${VERSION_MDI}/fonts/materialdesignicons-webfont.woff"

echo "Done! Static assets updated."
