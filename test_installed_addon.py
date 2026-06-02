"""Enable addon and test"""
import importlib, sys, os, bpy

# Enable from user addons directory
bpy.ops.preferences.addon_enable(module="uv_layer_manager_pro")

# Run the same tests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_uv_layer_manager_pro_blender import main
main()
