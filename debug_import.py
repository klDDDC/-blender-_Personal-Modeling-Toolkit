"""Quick debug: check if material_ops has unregister_properties"""
import importlib, sys, os
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

mod = importlib.import_module("uv_layer_manager_pro.material_ops")
print(f"material_ops loaded from: {getattr(mod, '__file__', 'unknown')}")
print(f"Has unregister_properties: {hasattr(mod, 'unregister_properties')}")
print(f"Has register_properties: {hasattr(mod, 'register_properties')}")
print(f"Module keys: {[k for k in dir(mod) if 'register' in k.lower() or 'unregister' in k.lower()]}")
