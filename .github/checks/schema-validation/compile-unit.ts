import { Ajv2020 } from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import { OpenApiConverter } from '@typia/utils';
import type { IJsonSchemaUnit } from 'typia';

export function compileUnit<Type>(unit: IJsonSchemaUnit<'3.1', Type>) {
  const components = OpenApiConverter.downgradeComponents(unit.components, '3.1');
  const schema = OpenApiConverter.downgradeSchema({
    components: unit.components,
    schema: unit.schema,
    version: '3.1',
    downgraded: components,
  });
  const ajv = new Ajv2020({
    strict: true, validateSchema: true,
    coerceTypes: false, useDefaults: false, removeAdditional: false,
  });
  ajv.addKeyword({ keyword: 'example' });
  addFormats(ajv);
  for (const [name, definition] of Object.entries(components.schemas ?? {})) {
    ajv.addSchema(definition, `#/components/schemas/${name}`);
  }
  return { validate: ajv.compile<Type>(schema), schema, components };
}
