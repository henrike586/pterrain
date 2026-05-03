"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    Import support for Pillow (PIL).

"""
import importlib
import site
import subprocess
import sys
import bpy

# Global variable to hold the imported Image module from Pillow
Image = None

def _get_modules_path():
    """
    Return Blender's user modules directory.
    """
    return bpy.utils.user_resource("SCRIPTS", path="modules", create=True)


def _append_modules_to_sys_path(modules_path):
    """
    Ensure modules installed in the target directory are found by Python.
    """
    if modules_path not in sys.path:
        sys.path.append(modules_path)
    site.addsitedir(modules_path)


def _install_pillow() -> None:
    """
    Install Pillow into Blender's bundled Python interpreter.
    """
    try:
        import ensurepip
    except Exception as exc:
        raise ImportError(
            'Pillow is required for this add-on, but pip is not available in Blender Python. '
            'Please install pip or Pillow manually for Blender.'
        ) from exc

    try:
        ensurepip.bootstrap()
    except Exception:
        pass

    modules_path = _get_modules_path()
    _append_modules_to_sys_path(modules_path)

    install_cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', '--target', modules_path, 'Pillow']
    try:
        subprocess.check_call(install_cmd)
    except subprocess.CalledProcessError as exc:
        raise ImportError(
            f'Failed to install Pillow into Blender Python. Run "{sys.executable} -m pip install --target {modules_path} Pillow" manually.'
        ) from exc


def import_pillow():
    """
    Return the PIL Image module, installing Pillow on demand if needed.
    """
    global Image
    if Image is not None:
        return Image

    try:
        modules_path = _get_modules_path()
    except:
        # This is a hack for running the code outside of Blender for testing purposes. 
        # It assumes Pillow is already installed in the environment.
        from PIL import Image as _Image
        Image = _Image
        return Image

    _append_modules_to_sys_path(modules_path)

    try:
        from PIL import Image as _Image
        Image = _Image
        return Image
    except ImportError:
        _install_pillow()
        importlib.invalidate_caches()
        _append_modules_to_sys_path(modules_path)
        try:
            from PIL import Image as _Image
            Image = _Image
            return Image
        except ImportError as exc:
            raise ImportError(
                'Pillow is required by PTerrain and installation failed. '
                'Install Pillow manually for Blender Python.'
            ) from exc
