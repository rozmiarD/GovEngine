from __future__ import annotations

from copy import deepcopy
from typing import Any


POLICY_SCHEMA_KINDS = (
    'policy-pack',
    'policy-pack-v1',
    'policy-request',
    'policy-verdict',
)


_POLICY_RULE_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'required': ['conditions'],
    'allOf': [
        {
            'oneOf': [
                {'required': ['rule_id']},
                {'required': ['id']},
            ]
        },
        {
            'oneOf': [
                {'required': ['effect']},
                {'required': ['decision']},
            ]
        },
    ],
    'additionalProperties': False,
    'properties': {
        'rule_id': {'type': 'string', 'minLength': 1},
        'id': {'type': 'string', 'minLength': 1},
        'effect': {'enum': ['allow', 'allow_with_obligations', 'approval_required', 'deny']},
        'decision': {
            'enum': ['allow', 'allow_with_obligations', 'approval_required', 'deny']
        },
        'conditions': {
            'type': 'object',
            'minProperties': 1,
            'additionalProperties': {
                'type': ['string', 'number', 'integer', 'boolean', 'null'],
            },
        },
        'priority': {'type': 'integer'},
        'reason_code': {'type': 'string'},
        'risk_class': {'enum': ['low', 'medium', 'high', 'critical']},
        'risk_score': {'type': 'number', 'minimum': 0, 'maximum': 1},
        'obligations': {
            'type': 'array',
            'items': {
                'type': 'object',
                'required': ['obligation_id', 'kind'],
                'properties': {
                    'obligation_id': {'type': 'string', 'minLength': 1},
                    'kind': {'type': 'string', 'minLength': 1},
                    'description': {'type': 'string'},
                    'metadata': {'type': 'object'},
                },
            },
        },
        'constraints': {
            'type': 'array',
            'items': {
                'type': 'object',
                'required': ['constraint_id', 'kind'],
                'properties': {
                    'constraint_id': {'type': 'string', 'minLength': 1},
                    'kind': {'type': 'string', 'minLength': 1},
                    'value': {},
                    'metadata': {'type': 'object'},
                },
            },
        },
    },
}

_POLICY_CONDITION_V1_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'required': ['path', 'operator', 'value'],
    'additionalProperties': False,
    'properties': {
        'path': {
            'type': 'string',
            'pattern': (
                '^(principal|action|resource|request_context|context)'
                '\\.[A-Za-z_][A-Za-z0-9_-]*'
                '(\\.[A-Za-z_][A-Za-z0-9_-]*)*$'
            ),
        },
        'operator': {
            'enum': [
                'eq',
                'neq',
                'in',
                'not_in',
                'contains',
                'exists',
                'lt',
                'lte',
                'gt',
                'gte',
                'subset_of',
                'matches_namespace',
            ],
        },
        'value': {},
    },
}

_POLICY_RULE_V1_SCHEMA = deepcopy(_POLICY_RULE_SCHEMA)
_POLICY_RULE_V1_SCHEMA['required'] = ['rule_id', 'effect', 'conditions']
_POLICY_RULE_V1_SCHEMA.pop('allOf')
_POLICY_RULE_V1_SCHEMA['properties'].pop('id')
_POLICY_RULE_V1_SCHEMA['properties'].pop('decision')
_POLICY_RULE_V1_SCHEMA['properties']['conditions'] = {
    'type': 'array',
    'minItems': 1,
    'items': _POLICY_CONDITION_V1_SCHEMA,
}


_SCHEMAS: dict[str, dict[str, Any]] = {
    'policy-pack': {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'https://govengine.local/schemas/policy-pack.v0.1.schema.json',
        'title': 'GovEngine policy pack',
        'description': 'Declarative governance policy input compiled by GovEngine; not SCLite truth and not execution authority.',
        'type': 'object',
        'required': ['version', 'rules'],
        'oneOf': [
            {'required': ['policy_id']},
            {'required': ['id']},
        ],
        'additionalProperties': False,
        'properties': {
            'policy_id': {'type': 'string', 'minLength': 1},
            'id': {'type': 'string', 'minLength': 1},
            'version': {'type': 'string', 'minLength': 1},
            'schema_version': {'const': 'v0.1'},
            'rules': {'type': 'array', 'minItems': 1, 'items': _POLICY_RULE_SCHEMA},
            'metadata': {'type': 'object'},
        },
    },
    'policy-pack-v1': {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'https://govengine.local/schemas/policy-pack.v1.schema.json',
        'title': 'GovEngine typed policy pack v1',
        'description': 'Typed deterministic governance policy input compiled by GovEngine; not SCLite truth and not execution authority.',
        'type': 'object',
        'required': [
            'policy_id',
            'version',
            'schema_version',
            'issuer_ref',
            'policy_epoch',
            'validity',
            'rules',
        ],
        'additionalProperties': False,
        'properties': {
            'policy_id': {'type': 'string', 'minLength': 1},
            'version': {'type': 'string', 'minLength': 1},
            'schema_version': {'const': 'v1'},
            'issuer_ref': {'type': 'string', 'minLength': 1},
            'policy_epoch': {'type': 'integer', 'minimum': 0},
            'validity': {
                'type': 'object',
                'required': ['not_before', 'expires_at'],
                'additionalProperties': False,
                'properties': {
                    'not_before': {'type': 'string', 'format': 'date-time'},
                    'expires_at': {'type': 'string', 'format': 'date-time'},
                },
            },
            'supersedes': {
                'type': 'array',
                'items': {'type': 'string', 'minLength': 1},
                'uniqueItems': True,
            },
            'rules': {'type': 'array', 'minItems': 1, 'items': _POLICY_RULE_V1_SCHEMA},
            'metadata': {'type': 'object'},
        },
    },
    'policy-request': {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'https://govengine.local/schemas/policy-request.v0.1.schema.json',
        'title': 'GovEngine policy request',
        'description': 'Bounded host-supplied policy evaluation input; raw command/evidence/credential payloads are forbidden by runtime validators.',
        'type': 'object',
        'required': ['request_id', 'subject_ref'],
        'additionalProperties': False,
        'properties': {
            'request_id': {'type': 'string', 'minLength': 1},
            'subject_ref': {'type': 'string', 'minLength': 1},
            'schema_version': {'const': 'v0.1'},
            'principal': {'type': 'object'},
            'action': {'type': 'object'},
            'resource': {'type': 'object'},
            'context': {'type': 'object'},
            'evidence_refs': {'type': 'array', 'items': {'type': 'string'}},
            'metadata': {'type': 'object'},
        },
    },
    'policy-verdict': {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'https://govengine.local/schemas/policy-verdict.v0.1.schema.json',
        'title': 'GovEngine policy verdict',
        'description': 'Deterministic GovEngine policy result suitable for admission projection.',
        'type': 'object',
        'required': ['verdict_id', 'request_id', 'subject_ref', 'decision'],
        'additionalProperties': False,
        'properties': {
            'verdict_id': {'type': 'string', 'minLength': 1},
            'request_id': {'type': 'string', 'minLength': 1},
            'subject_ref': {'type': 'string', 'minLength': 1},
            'schema_version': {'const': 'v0.1'},
            'decision': {'enum': ['allow', 'allow_with_obligations', 'approval_required', 'deny']},
            'reason_code': {'type': 'string'},
            'risk_class': {'enum': ['low', 'medium', 'high', 'critical']},
            'risk_score': {'type': 'number', 'minimum': 0, 'maximum': 1},
            'obligations': {'type': 'array'},
            'constraints': {'type': 'array'},
            'blockers': {'type': 'array', 'items': {'type': 'string'}},
            'evidence_refs': {'type': 'array', 'items': {'type': 'string'}},
            'metadata': {'type': 'object'},
        },
    },
}


def policy_json_schema(kind: str = 'policy-pack') -> dict[str, Any]:
    normalized = str(kind or '').strip()
    schema = _SCHEMAS.get(normalized)
    if schema is None:
        raise KeyError(normalized)
    return deepcopy(schema)
