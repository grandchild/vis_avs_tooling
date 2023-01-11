import { builtin, dll, ComponentDefinition } from "../webvsc/src/lib/components"

let all: ComponentDefinition[] = [];
for(let c of builtin) {
    all.push(c);
}
for(let c of dll) {
    all.push(c);
}
console.log(JSON.stringify(all, null, "  "));
