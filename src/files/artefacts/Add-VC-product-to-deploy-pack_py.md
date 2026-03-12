# Mission: Add VC product to deploy-pack.py

This mission involves including the vCenter (VC) product in the automated packaging process managed by `tools/deploy-pack.py`.

## Analysis Summary
- **Logic**: The `deploy-pack.py` script uses a hardcoded list `product_list` on line 9 to determine which products to include in the ZIP package.
- **Pattern**: For each product in the list, the script expects a standard set of files in `src/{product}/`:
  - `__init__.py`
  - `{product}getinfo.py`
  - `{product}processinfo.py`
  - `{product}createreportDC.py`
  - `{product}createreportDCI.py`
- **Current State**: The `src/VC` directory already contains the required python scripts, but was missing the `__init__.py` file which is present in all other product directories.

## Branch Created
`feature/add-vc-product-to-deploy-pack`

## Proposed Changes

### 1. tools/deploy-pack.py
Add 'VC' to the `product_list` variable to trigger the inclusion of VC files during packaging.

```diff
--- a/tools/deploy-pack.py
+++ b/tools/deploy-pack.py
@@ -6,7 +6,7 @@
 import subprocess
 import shlex
 
-product_list =  ['DD', 'ECS', 'IDRAC', 'OS10', 'PPCR', 'PPDM']
+product_list =  ['DD', 'ECS', 'IDRAC', 'OS10', 'PPCR', 'PPDM', 'VC']
 
 deploy_file_list = [
     "src/DCO-DailyCheck.py",
```

### 2. src/VC/__init__.py
Created an empty `__init__.py` file to maintain consistency with other products and ensure the packaging script finds all expected files without warnings.

### 3. src/common/__init__.py
Created an empty `__init__.py` file in the common utilities directory to resolve a missing file warning during packaging and ensure consistent Python package structure.

## Verification Results
- **Execution**: Ran `python tools/deploy-pack.py` after the final adjustments.
- **Output**:
  ```
  Creating deploy pack with products: DD, ECS, IDRAC, OS10, PPCR, PPDM, VC
  Deploy pack file: build/deploypack-20260312_1616.zip
  ```
- **Confirmation**: All warnings have been resolved. The script now processes all 7 products cleanly, including the complete vCenter module.

## Expected Outcome
When users run the `deploy-pack.py` tool, the resulting ZIP file in the `build/` directory will now contain the complete set of vCenter scripts, allowing for a full deployment of the vCenter check module alongside the other products.
