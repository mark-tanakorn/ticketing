"""
Code Validator - Security and correctness validation for custom node code

Uses AST parsing to validate Python code structure and enforce security rules.
Prevents dangerous imports and patterns.
"""

import ast
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class NodeCodeValidator:
    """
    Validates custom node code for security and correctness.
    
    Security checks:
    - Import whitelist enforcement
    - Dangerous pattern detection (eval, exec, os.system, etc.)
    - File system access restrictions
    
    Correctness checks:
    - Valid Python syntax
    - Required class structure
    - Decorator presence
    - Required methods
    """
    
    # Allowed imports (whitelist)
    ALLOWED_IMPORTS = {
        'app.core.nodes.base',
        'app.core.nodes.registry',
        'app.core.nodes.capabilities',
        'app.core.nodes.multimodal',
        'app.core.nodes.safe_io',
        'app.schemas.workflow',
        'typing',
        'dataclasses',
        'enum',
        'logging',
        'json',
        'datetime',
        'email',
        'imaplib',
        'httpx',
        'urllib.parse',
        'urllib.request',
        'urllib.error',
        'uuid',
        'hashlib',
        'hmac',
        'base64',
        'decimal',
        'zoneinfo',
        'csv',
        'html',
        'collections',
        'functools',
        'itertools',
        'math',
        'pathlib',
        'pydantic',
        're',
        'time',
        'asyncio',
    }
    
    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r'\beval\s*\(',
        r'\bexec\s*\(',
        r'\b__import__\s*\(',
        r'\bcompile\s*\(',
        r'\bsubprocess\.',
        r'\bos\.system\s*\(',
        r'\bos\.popen\s*\(',
        r'\bos\.exec',
        r'\bopen\s*\(',  # Restrict direct file operations (use safe_io instead)
    ]
    
    def validate(self, code: str) -> Dict[str, Any]:
        """
        Validate node code.
        
        Args:
            code: Python code to validate
        
        Returns:
            Dict with:
            - valid: Boolean indicating if code is valid
            - errors: List of error messages
            - warnings: List of warning messages
            - node_type: Extracted node type (if valid)
            - class_name: Extracted class name (if valid)
        """
        errors = []
        warnings = []
        node_type = None
        class_name = None
        
        logger.info("🔍 Validating node code...")
        
        # 1. Syntax check
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "node_type": None,
                "class_name": None
            }
        
        # 2. Check imports
        import_errors = self._check_imports(tree)
        errors.extend(import_errors)
        
        # 3. Check for dangerous patterns
        pattern_errors = self._check_dangerous_patterns(code)
        errors.extend(pattern_errors)

        # 3b. Block direct filesystem access patterns (use app.core.nodes.safe_io for reads)
        fs_errors = self._check_filesystem_usage(tree)
        errors.extend(fs_errors)
        
        # 4. Check class structure
        structure_result = self._check_class_structure(tree)
        errors.extend(structure_result["errors"])
        warnings.extend(structure_result["warnings"])
        class_name = structure_result.get("class_name")
        
        # 5. Check decorator
        decorator_result = self._check_decorator(tree)
        errors.extend(decorator_result["errors"])
        node_type = decorator_result.get("node_type")
        
        # 6. Check required methods
        method_errors = self._check_required_methods(tree)
        errors.extend(method_errors)
        
        valid = len(errors) == 0
        
        if valid:
            logger.info(f"✅ Validation passed: {node_type}")
        else:
            logger.warning(f"❌ Validation failed: {len(errors)} errors")
        
        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "node_type": node_type,
            "class_name": class_name
        }
    
    def _check_imports(self, tree: ast.AST) -> List[str]:
        """Check if all imports are in the whitelist"""
        errors = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not self._is_allowed_import(alias.name):
                        errors.append(f"Forbidden import: '{alias.name}' (not in whitelist)")
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if not self._is_allowed_import(module):
                    errors.append(f"Forbidden import: 'from {module}' (not in whitelist)")
        
        return errors
    
    def _is_allowed_import(self, module_name: str) -> bool:
        """Check if module is in whitelist"""
        if not module_name:
            return True
        
        # Check exact match or prefix match
        for allowed in self.ALLOWED_IMPORTS:
            if module_name == allowed or module_name.startswith(allowed + '.'):
                return True
        
        return False
    
    def _check_dangerous_patterns(self, code: str) -> List[str]:
        """Check for dangerous code patterns"""
        errors = []
        
        for pattern in self.DANGEROUS_PATTERNS:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                # Calculate line number
                line_num = code[:match.start()].count('\n') + 1
                errors.append(f"Dangerous pattern at line {line_num}: {match.group()}")
        
        return errors

    def _check_filesystem_usage(self, tree: ast.AST) -> List[str]:
        """
        Prevent direct filesystem access from custom node code.

        Custom nodes run inside the backend process; even on "local" deployments, we should
        avoid letting generated code read arbitrary files on disk. If file reads are needed,
        require the safe helper: app.core.nodes.safe_io.safe_read_text / safe_read_bytes / safe_read_json.
        """
        errors: List[str] = []

        # Detect whether pathlib is imported (then forbid common file I/O methods on Path objects)
        pathlib_imported = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "pathlib":
                        pathlib_imported = True
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "") == "pathlib":
                    pathlib_imported = True

        forbidden_path_ops = {
            # reads (require safe_io)
            "read_text",
            "read_bytes",
            "open",
            # writes / deletes (never allowed)
            "write_text",
            "write_bytes",
            "unlink",
            "rmdir",
            "mkdir",
            "rename",
            "replace",
        }

        if pathlib_imported:
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in forbidden_path_ops:
                        errors.append(
                            f"Direct filesystem access via pathlib.{node.func.attr}() is not allowed. "
                            f"Use app.core.nodes.safe_io for safe, allowlisted file reads."
                        )

        return errors
    
    def _check_class_structure(self, tree: ast.AST) -> Dict[str, Any]:
        """Check if code has proper class structure"""
        errors = []
        warnings = []
        class_name = None
        
        # Find class definitions
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        if not classes:
            errors.append("No class definition found (must define a Node class)")
            return {"errors": errors, "warnings": warnings}
        
        if len(classes) > 1:
            warnings.append(f"Multiple classes found ({len(classes)}), using first one")
        
        node_class = classes[0]
        class_name = node_class.name
        
        # Check if class inherits from Node
        has_node_base = False
        if node_class.bases:
            for base in node_class.bases:
                if isinstance(base, ast.Name) and base.id == 'Node':
                    has_node_base = True
                    break
        
        if not has_node_base:
            errors.append(f"Class '{class_name}' must inherit from 'Node'")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "class_name": class_name
        }
    
    def _check_decorator(self, tree: ast.AST) -> Dict[str, Any]:
        """Check for @register_node decorator"""
        errors = []
        node_type = None
        
        # Find class definitions
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        if not classes:
            return {"errors": errors, "node_type": None}
        
        node_class = classes[0]
        
        # Check for decorator
        has_register_decorator = False
        
        for decorator in node_class.decorator_list:
            # Handle @register_node(...) call
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == 'register_node':
                    has_register_decorator = True
                    # Extract node_type from decorator arguments
                    for keyword in decorator.keywords:
                        if keyword.arg == 'node_type':
                            if isinstance(keyword.value, ast.Constant):
                                node_type = keyword.value.value
            
            # Handle @register_node (without call)
            elif isinstance(decorator, ast.Name) and decorator.id == 'register_node':
                has_register_decorator = True
        
        if not has_register_decorator:
            errors.append("Missing @register_node decorator")
        
        if has_register_decorator and not node_type:
            errors.append("@register_node decorator must specify node_type")
        
        return {
            "errors": errors,
            "node_type": node_type
        }
    
    def _check_required_methods(self, tree: ast.AST) -> List[str]:
        """Check if required methods are present"""
        errors = []
        
        # Find class definitions
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        if not classes:
            return errors
        
        node_class = classes[0]
        
        # Get method names
        methods = [node.name for node in node_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        
        # Check required class methods
        required_class_methods = ['get_input_ports', 'get_output_ports', 'get_config_schema']
        
        for method_name in required_class_methods:
            if method_name not in methods:
                errors.append(f"Missing required class method: {method_name}()")
        
        # Check execute method
        if 'execute' not in methods:
            errors.append("Missing required method: execute()")
        else:
            # Check if execute is async
            execute_methods = [
                node for node in node_class.body 
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'execute'
            ]
            
            if execute_methods:
                execute_method = execute_methods[0]
                if not isinstance(execute_method, ast.AsyncFunctionDef):
                    errors.append("execute() method must be async (use 'async def execute')")
        
        return errors

