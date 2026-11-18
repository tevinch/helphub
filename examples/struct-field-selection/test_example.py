"""Run with python -m unittest -v."""

import copy
import unittest
from typing import Annotated

import msgspec
from msgspec import inspect as mi

import example


class FieldSelectionTests(unittest.TestCase):
    def test_kind_dispatch_traverses_both_structs_and_calls_handlers(self):
        # Wrong descriptor-instance keys, missing traversal, or skipped handlers fail.
        inventory, change = example.sample_records()
        self.assertEqual(example.select_by_kind(inventory), [
            ('count', 'integer:3'),
            ('positive_count', 'integer:2'),
            ('minimum_count', 'integer:10'),
            ('numbers', 'list:2'),
            ('labels', 'list:1'),
        ])
        self.assertEqual(example.select_by_kind(change), [
            ('delta', 'integer:-1'),
            ('positive_delta', 'integer:4'),
            ('tags', 'list:2'),
        ])

    def test_exact_dispatch_keeps_constraints_items_and_metadata(self):
        # Dropping bounds, item types, or Metadata would add incorrect matches.
        inventory, change = example.sample_records()
        self.assertEqual(example.select_exact(inventory), [
            ('count', 'plain integer:3'),
            ('positive_count', 'positive integer:2'),
            ('numbers', 'integer list:2'),
            ('documented_count', 'documented integer:7'),
        ])
        self.assertEqual(example.select_exact(change), [
            ('delta', 'plain integer:-1'),
            ('positive_delta', 'positive integer:4'),
            ('documented_delta', 'documented integer:8'),
        ])
        fields = mi.type_info(example.Inventory).fields
        by_name = {field.name: field.type for field in fields}
        self.assertEqual(len(fields), 10)
        self.assertIsInstance(by_name['count'], mi.IntType)
        self.assertIsInstance(by_name['positive_count'], mi.IntType)
        self.assertIsInstance(by_name['enabled'], mi.BoolType)
        self.assertNotIsInstance(by_name['enabled'], mi.IntType)
        self.assertIsInstance(by_name['optional_count'], mi.UnionType)
        self.assertIsInstance(by_name['documented_count'], mi.Metadata)
        self.assertNotEqual(by_name['count'], by_name['positive_count'])
        self.assertNotEqual(by_name['positive_count'], by_name['minimum_count'])
        self.assertNotEqual(by_name['numbers'], by_name['labels'])
        self.assertNotEqual(by_name['documented_count'], by_name['count'])
        changed_title = mi.type_info(Annotated[
            int, msgspec.Meta(title='Other count', extra={'unit': 'items'})
        ])
        changed_extra = mi.type_info(Annotated[
            int, msgspec.Meta(title='Count', extra={'unit': 'boxes'})
        ])
        self.assertNotIn(changed_title, example.EXACT_TARGETS)
        self.assertNotIn(changed_extra, example.EXACT_TARGETS)

    def test_fresh_introspection_repeats_without_changing_models_or_values(self):
        # A selector mutating descriptors, model settings, or values fails here.
        for record in example.sample_records():
            with self.subTest(model=type(record).__name__):
                model = type(record)
                annotations = dict(model.__annotations__)
                before = copy.deepcopy(mi.type_info(model))
                encoded = msgspec.json.encode(record)
                self.assertIsInstance(before, mi.StructType)
                self.assertTrue(before.forbid_unknown_fields)
                self.assertFalse(before.array_like)
                kind = example.select_by_kind(record)
                exact = example.select_exact(record)
                for _ in range(2):
                    self.assertEqual(example.select_by_kind(record), kind)
                    self.assertEqual(example.select_exact(record), exact)
                    self.assertEqual(mi.type_info(model), before)
                self.assertEqual(model.__annotations__, annotations)
                self.assertEqual(msgspec.json.encode(record), encoded)
                self.assertEqual(msgspec.json.decode(encoded, type=model), record)
                payload = msgspec.json.decode(encoded)
                payload['unexpected'] = True
                with self.assertRaises(msgspec.ValidationError):
                    msgspec.json.decode(msgspec.json.encode(payload), type=model)
                payload.pop('unexpected')
                positive_field = 'positive_count' if model is example.Inventory else 'positive_delta'
                payload[positive_field] = 0
                with self.assertRaises(msgspec.ValidationError):
                    msgspec.json.decode(msgspec.json.encode(payload), type=model)

    def test_selectors_use_the_supplied_record_and_allow_no_matches(self):
        # Hard-coded sample results or an implicit catch-all handler fail.
        class Small(msgspec.Struct):
            quantity: int
            names: list[str]
            active: bool
        class TextOnly(msgspec.Struct):
            text: str
        value = Small(12, ['x', 'y', 'z'], True)
        self.assertEqual(example.select_by_kind(value), [
            ('quantity', 'integer:12'), ('names', 'list:3')
        ])
        self.assertEqual(example.select_exact(value), [('quantity', 'plain integer:12')])
        self.assertEqual(example.select_by_kind(TextOnly('hello')), [])
        self.assertEqual(example.select_exact(TextOnly('hello')), [])

    def test_inspected_field_descriptor_still_has_native_hash_behavior(self):
        # Selection must not obtain its result by monkey-patching Type hashing.
        field = mi.type_info(example.Inventory).fields[0]
        with self.assertRaises(TypeError):
            {field.type}
        with self.assertRaises(TypeError):
            {field.type: 'handler'}


if __name__ == '__main__':
    unittest.main()
