import { unit } from './model.js';
import { compileUnit } from './compile-unit.js';

const { validate } = compileUnit(unit);
const input: unknown = {
  id: '123e4567-e89b-42d3-a456-426614174000',
  age: 42,
  email: 'person@example.com',
  address: { city: 'London', postalCode: '12345' },
};
console.log(JSON.stringify({ valid: validate(input), errors: validate.errors ?? null }, null, 2));
