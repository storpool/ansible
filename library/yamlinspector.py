#!/usr/bin/python
"""Ansible module for validation by schema."""
import yaml
from ansible.module_utils.basic import AnsibleModule  # type: ignore
from cerberus import Validator  # type: ignore


def load_schema(schema_path):
    """Load SCHEMA YAML file."""
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"YAML Syntax Error: {e}")
        return None


def validate_yaml(data, schema):
    """Validate YAML against schema."""
    v = Validator(schema)
    errors = None
    is_valid = v.validate(data)
    if not is_valid:
        errors = v.errors
    return errors


def main():
    """Ansible module for YAML validation main function."""
    schema_path = "validation_schema/storpool-schema.yaml"
    module = AnsibleModule(
        argument_spec={
            "file_content": {"type": "str", "required": True},
            "schema": {
                "type": "dict",
                "required": False,
                "default": load_schema(schema_path=schema_path),
            },
        },
        supports_check_mode=True,
    )

    file_content = module.params["file_content"]
    schema = module.params["schema"]

    result = {
        "changed": False,
        "validation_errors": None,
    }

    try:
        yaml_data = yaml.safe_load(file_content)
        validation_errors = validate_yaml(yaml_data, schema)
        result["validation_errors"] = validation_errors
        if validation_errors is None:
            result["msg"] = "YAML is valid."
        else:
            result["msg"] = "YAML validation failed."
            module.fail_json(msg=f"{result['msg']}\n{result['validation_errors']}")
    except yaml.YAMLError as e:
        module.fail_json(msg=f"YAML syntax error: {str(e)}")

    module.exit_json(**result)


if __name__ == "__main__":
    main()
