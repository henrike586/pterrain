"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    Add-on entry/exit functions, and UI handling.

"""
import bpy
import blf
import gpu
import math
import time
from . src import settings
from . src import presets
from . src import dem_layer
from . src import map_layer
from . src import blender_object
from . src import web_mercator
from . src import proj_geocentric
from . src import proj_orthographic

# Global variables for viewport message handling
g_viewport_message = ''
g_viewport_draw_handler = None


def register_draw_handler() -> None:
    """
    Register draw handler for 3D viewport.
    """
    global g_viewport_draw_handler
    if g_viewport_draw_handler is None:
        g_viewport_draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_g_viewport_message,
            (),
            'WINDOW',
            'POST_PIXEL'
        )


def unregister_draw_handler() -> None:
    """
    Unregister draw handler for 3D viewport.
    """
    global g_viewport_draw_handler
    if g_viewport_draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(g_viewport_draw_handler, 'WINDOW')
        g_viewport_draw_handler = None


def update_g_viewport_message(text : str) -> None:
    """
    Update the message displayed in the 3D viewport.

    Parameters 
    ---------
    text : str
        The text message to display in the viewport.
    """
    global g_viewport_message
    if(len(text) > 0):
        g_viewport_message = 'PTerrain - ' + text
    else:
        g_viewport_message = ''
    request_g_viewport_redraw()


def request_g_viewport_redraw() -> None:
    """
    Request a redraw of the 3D viewport.
    """
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    try:
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    except Exception:
        pass


def draw_g_viewport_message() -> None:
    """
    Draw the message in the 3D viewport.
    """
    # Blend state for text overlay
    bmode = gpu.state.blend_get()
    dmode = gpu.state.depth_test_get()
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')

    # Font settings
    font_id = 0
    blf.position(font_id, 60, 60, 0)
    blf.size(font_id, 36.0)
    blf.color(font_id, 1.0, 1.0, 1.0, 1.0)

    # Draw each line of the message
    for line_index, line in enumerate(g_viewport_message.splitlines()):
        blf.position(font_id, 60, 60 + 22 * line_index, 0)
        blf.draw(font_id, line)

    # Restore previous GPU state
    gpu.state.blend_set(bmode)
    gpu.state.depth_test_set(dmode)


def show_error_dialog(message : str) -> None:
    """
    Show an error dialog with the specified message.

    Parameters 
    ---------
    message : str
        The error message to display.
    """
    def draw(self, context):
        self.layout.label(text='An error occurred during generation.')
        for line in message.splitlines():
            self.layout.label(text=line)

    bpy.context.window_manager.popup_menu(draw, title='PTerrain Error', icon='ERROR')


def generate() -> None:
    """
    Generate the terrain.
    """
    props = bpy.context.scene.pterrain_props

    # Check if allowed to access the internet for tile fetching
    if not bpy.app.online_access:
        show_error_dialog('Online access is disabled. Please enable it to use PTerrain.')
        return

    # Parse center position
    ll = props.position.split(',')
    if len(ll) != 2:
        raise ValueError('Invalid position format. Expected lat, lon.')
    latc = float(ll[0].strip())
    lonc = float(ll[1].strip()) 
    settings.PT_SETTINGS['lonc'] = lonc
    settings.PT_SETTINGS['latc'] = latc
    settings.PT_SETTINGS['grid_center_x'] = web_mercator.lon2wmx(settings.PT_SETTINGS['lonc'] * math.pi / 180.0)
    settings.PT_SETTINGS['grid_center_y'] = web_mercator.lat2wmy(settings.PT_SETTINGS['latc'] * math.pi / 180.0)

    # Set projection center to grid center if recentering is enabled
    if(props.recenter):
        settings.PT_SETTINGS['proj_center_x'] = settings.PT_SETTINGS['grid_center_x']
        settings.PT_SETTINGS['proj_center_y'] = settings.PT_SETTINGS['grid_center_y']

    # Set DEM and MAP presets based on user selection
    if(props.dem_resolution == 'LOW'):
        settings.PT_SETTINGS['dem_preset'] = presets.PT_DEM_PRESETS[0]
    elif(props.dem_resolution == 'MEDIUM'):
        settings.PT_SETTINGS['dem_preset'] = presets.PT_DEM_PRESETS[1]
    elif(props.dem_resolution == 'HIGH'):
            settings.PT_SETTINGS['dem_preset'] = presets.PT_DEM_PRESETS[2]

    if(props.map_resolution == 'LOW'):
        settings.PT_SETTINGS['map_preset'] = presets.PT_MAP_PRESETS[0]
    elif(props.map_resolution == 'MEDIUM'):
        settings.PT_SETTINGS['map_preset'] = presets.PT_MAP_PRESETS[1]
    elif(props.map_resolution == 'HIGH'):
        settings.PT_SETTINGS['map_preset'] = presets.PT_MAP_PRESETS[2]

    # Set projection method based on user selection
    if(props.projection == 'GEOCENTRIC'):
        proj = proj_geocentric.proj_geocentric(settings.PT_SETTINGS['proj_center_x'], settings.PT_SETTINGS['proj_center_y'])
    elif(props.projection == 'ORTHOGRAPHIC'):
        proj = proj_orthographic.proj_orthographic(settings.PT_SETTINGS['proj_center_x'], settings.PT_SETTINGS['proj_center_y'])
    elif(props.projection == 'WEBMERCATOR'):
        proj = web_mercator.proj_web_mercator(settings.PT_SETTINGS['proj_center_x'], settings.PT_SETTINGS['proj_center_y'])

    # Set clamp to sea level setting
    settings.PT_SETTINGS['clamp_to_sea_level'] = props.clamp_sea_level

    # Build DEM and MAP layers, and generate the Blender object
    dem_tile_url = bpy.context.preferences.addons[__name__].preferences.dem_tile_url
    map_tile_url = bpy.context.preferences.addons[__name__].preferences.map_tile_url
    dem_layers = dem_layer.build_dems(dem_tile_url, update_g_viewport_message)
    map_layers = map_layer.build_maps(map_tile_url, update_g_viewport_message)
    if(props.snap_center_z):
        proj.set_z_offset(-dem_layers[0][1].center_height)
    obj = blender_object.build_blender_object(dem_layers, map_layers, proj, update_g_viewport_message)

    # Adjust view clipping planes if enabled
    if(props.adjust_view):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.clip_start = 100
                        space.clip_end = 1e7

    # Clear viewport message
    update_g_viewport_message('')


class PTerrainProperties(bpy.types.PropertyGroup):
    """
    PTerrain properties for the UI panel.
    """
    position: bpy.props.StringProperty(
        name='Lat, lon',
        description='Center position for terrain generation.',
        default='45.976619, 7.657492'
    )

    dem_resolution: bpy.props.EnumProperty(
        name='DEM resolution',
        description='DEM resolution for generated terrain.',
        items=[
            ('LOW', 'Low', 'Low DEM resolution'),
            ('MEDIUM', 'Medium', 'Medium DEM resolution'),
            ('HIGH', 'High', 'High DEM resolution'),
        ],
        default='LOW'
    )

    map_resolution: bpy.props.EnumProperty(
        name='MAP resolution',
        description='MAP resolution for generated terrain.',
        items=[
            ('LOW', 'Low', 'Low MAP resolution'),
            ('MEDIUM', 'Medium', 'Medium MAP resolution'),
            ('HIGH', 'High', 'High MAP resolution'),
        ],
        default='LOW'
    )

    projection: bpy.props.EnumProperty(
        name='Projection',
        description='Projection method for terrain generation.',
        items=[
            ('GEOCENTRIC', 'Geocentric', 'Geocentric projection'),
            ('ORTHOGRAPHIC', 'Orthographic', 'Orthographic projection'),
            ('WEBMERCATOR', 'Web Mercator', 'Web Mercator projection'),
        ],
        default='GEOCENTRIC'
    )

    recenter: bpy.props.BoolProperty(
        name='Re-center',
        description='Re-center generated terrain projection.',
        default=True
    )

    adjust_view: bpy.props.BoolProperty(
        name='Adjust clipping',
        description='Adjust the view clipping planes after generation.',
        default=True
    )

    snap_center_z: bpy.props.BoolProperty(
        name='Snap center elevation to z=0',
        description='Snap the center of the terrain to the z=0 plane.',
        default=False
    )

    clamp_sea_level: bpy.props.BoolProperty(
        name='Clamp elevation to sea level',
        description='Clamp the elevation to the sea level (i.e., set all elevations below zero to 0).',
        default=False
    )


class PTerrainGenerateOperator(bpy.types.Operator):
    """
    Generate operator.
    """
    bl_idname = 'pterrain.generate'
    bl_label = 'Generate'
    bl_description = 'Generate terrain with PTerrain'

    def execute(self, context):
        register_draw_handler()

        try:
            start_time = time.perf_counter()
            generate()
            elapsed = time.perf_counter() - start_time
            self.report({'INFO'}, f'PTerrain generation completed in {elapsed:.2f} seconds.')
        except Exception as exc:
            update_g_viewport_message('PTerrain: Error during generation.')
            show_error_dialog(str(exc))
            return {'CANCELLED'}

        return {'FINISHED'}


class PTerrainPanel(bpy.types.Panel):
    """
    UI panel for PTerrain.
    """
    bl_label = 'PTerrain'
    bl_idname = 'VIEW3D_PT_pterrain'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'PTerrain'

    def draw(self, context):
        """
        Draw the addon panel UI.

        Parameters 
        ---------
        context : bpy.types.Context
            The Blender context.
        """
        layout = self.layout
        props = context.scene.pterrain_props

        layout.prop(props, 'position')
        layout.prop(props, 'dem_resolution')
        layout.prop(props, 'map_resolution')
        layout.prop(props, 'projection')
        layout.prop(props, 'snap_center_z')
        layout.prop(props, 'recenter')
        layout.prop(props, 'adjust_view')
        layout.prop(props, 'clamp_sea_level')
        layout.operator(PTerrainGenerateOperator.bl_idname, text='Generate')


class PTerrainAddonPreferences(bpy.types.AddonPreferences):
    """
    Addon preferences for PTerrain.
    """
    bl_idname = __name__

    dem_tile_url: bpy.props.StringProperty(
        name='DEM URL',
        description='URL for the DEM tile data.',
        default='https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
    )

    map_tile_url: bpy.props.StringProperty(
        name='MAP URL',
        description='URL for the MAP tile data.',
        default='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'
    )

    def draw(self, context) -> None:
        """
        Draw the addon preferences UI.

        Parameters 
        ---------
        context : bpy.types.Context
            The Blender context.
        """
        layout = self.layout
        layout.prop(self, 'dem_tile_url')
        layout.prop(self, 'map_tile_url')


classes = (
    PTerrainProperties,
    PTerrainGenerateOperator,
    PTerrainPanel,
    PTerrainAddonPreferences,
)


def register() -> None:
    """
    Register the PTerrain addon.
    """
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.pterrain_props = bpy.props.PointerProperty(type=PTerrainProperties)
    register_draw_handler()


def unregister() -> None:
    """
    Unregister the PTerrain addon.
    """
    unregister_draw_handler()
    del bpy.types.Scene.pterrain_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

