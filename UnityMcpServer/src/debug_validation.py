#!/usr/bin/env python3
"""Debug validation issue."""

import sys
sys.path.insert(0, '.')

try:
    from validation import UnityToolValidators
    print("Creating manage_script validator...")
    validator = UnityToolValidators.create_manage_script_validator()
    print(f"Validator created: {validator}")
    print(f"Validator type: {type(validator)}")
    
    if validator:
        print(f"Parameter validators: {list(validator.parameter_validators.keys())}")
        
        # Test validation
        test_params = {
            "action": "create",
            "name": "TestScript",
            "path": "Assets/Scripts/",
            "contents": "// Test content",
            "script_type": "MonoBehaviour",
            "namespace": "TestNamespace"
        }
        
        print("Testing validation with valid parameters...")
        validator.validate(test_params)
        print("✓ Validation passed")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
