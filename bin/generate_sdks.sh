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

OUTPUT_DIR="./sdks"


for component in "${COMPONENTS[@]}";
do
    COMPONENT_PATH="./src/openzaak/components/${component}/openapi.yaml"
    OAS_CONTENTS=$("cat $COMPONENT_PATH")

    echo "Validating OAS for $COMPONENT_PATH"
    openapi-generator-cli validate -i "$OAS_CONTENTS"

    echo "Generating Java SDK for $component ..."
    openapi-generator-cli generate -i "$OAS_CONTENTS" \
        --global-property=modelTests=false,apiTests=false,modelDocs=false,apiDocs=false \
          -o "$OUTPUT_DIR/java" \
          -g java \
          --additional-properties=dateLibrary=java8,java8=true,optionalProjectFile=false,optionalAssemblyInfo=false

    echo "Generating .NET SDK for $component ..."
    openapi-generator-cli generate -i "$OAS_CONTENTS" \
        --global-property=modelTests=false,apiTests=false,modelDocs=false,apiDocs=false \
          -o "$OUTPUT_DIR/net" \
          -g csharp \
          --additional-properties=optionalProjectFile=false,optionalAssemblyInfo=false

    echo "Generating Python SDK for $component ..."
    openapi-generator-cli generate -i "$OAS_CONTENTS" \
        --global-property=modelTests=false,apiTests=false,modelDocs=false,apiDocs=false \
        -o "$OUTPUT_DIR/python" \
        -g python \
        --additional-properties=optionalProjectFile=false,optionalAssemblyInfo=false+
done
