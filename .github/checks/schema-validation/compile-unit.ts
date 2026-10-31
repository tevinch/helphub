import { Ajv2020 } from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import type { IJsonSchemaUnit } from 'typia';

export function compileUnit<Type>(unit: IJsonSchemaUnit<'3.1', Type>) {
  const components = unit.components;
  const schema = unit.schema;
  const ajv = new Ajv2020({
    strict: true, validateSchema: true,
    coerceTypes: false, useDefaults: false, removeAdditional: false,
  });
  addFormats(ajv);
  for (const [name, definition] of Object.entries(components.schemas ?? {})) {
    ajv.addSchema(definition, `#/components/schemas/${name}`);
  }
  return { validate: ajv.compile<Type>(schema), schema, components };
}
