#!/bin/bash

# Run this script from the root of the repository

set -e

COMPONENTS=(
    autorisaties
    besluiten
    catalogi
    documenten
    zaken
)

if [[ -z "$VIRTUAL_ENV" ]] && [[ ! -v GITHUB_ACTIONS ]]; then
    echo "You need to activate your virtual env before running this script"
    exit 1
fi

for component in "${strings[@]}";
do
    ./bin/generate_schema_for_component "$component" "openapi-$component.yaml"

    diff "openapi-$component.yaml" "src/openzaak/components/$component/openapi.yaml"

    if (( $? > 0 )); then
        echo "Component src/openzaak/components/$component/openapi.yaml needs to be updated!"
    fi
done
