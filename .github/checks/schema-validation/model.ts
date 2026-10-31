import typia, { tags } from 'typia';

export interface Address {
  city: string & tags.MinLength<1>;
  postalCode: string & tags.Pattern<'^[0-9]{5}$'>;
}

export interface User {
  id: string & tags.Format<'uuid'>;
  age: number & tags.Type<'uint32'>;
  email?: string & tags.Format<'email'> & tags.Examples<{ sample: 'person@example.com' }>;
  address: Address;
}

// This call requires the native typia transform; no schema is handwritten.
export const unit = typia.json.schema<User>();
