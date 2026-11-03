"""Explicit capability hints for the pinned EPLAN tool catalog.

These classifications are informational MCP annotations, not authorization.
New built-ins must be reviewed and added; unknown extensions default to the
conservative arbitrary-execution category.  File I/O can also modify projects.
"""

from mcp.types import ToolAnnotations


def _names(text):
    return frozenset(text.split())


# Explicit snapshot of pinned built-ins. Do not infer read-only from prefixes.
BUILTIN_CATEGORIES = {
    "read_only": _names("""
        aas_inspect_package
        eplan_action_catalog
        eplan_action_describe
        eplan_api_describe
        eplan_api_types
        eplan_get_current_project
        eplan_get_page_property
        eplan_get_project_property
        eplan_get_property
        eplan_get_selected_pages
        eplan_get_system_messages
        eplan_list_enums
        eplan_list_extensions
        eplan_list_layers
        eplan_list_report_templates
        eplan_list_schemes
        eplan_live_query_functions
        eplan_live_query_pages
        eplan_live_read_check_messages
        eplan_live_read_connections
        eplan_live_read_page
        eplan_live_routing_catalog
        eplan_live_symbol_catalog
        eplan_live_verify_page
        eplan_parts_db_count
        eplan_parts_db_get_part
        eplan_parts_db_list_product_groups
        eplan_parts_db_query
        eplan_pathmap_get_common_paths
        eplan_pathmap_substitute
        eplan_ping
        eplan_ribbon_catalog
        eplan_scratch_project_list
        eplan_search_all_properties
        eplan_search_devices
        eplan_search_page_data
        eplan_search_project_data
        eplan_search_text
        eplan_servers
        eplan_settings_get_bool
        eplan_settings_get_double
        eplan_settings_get_int
        eplan_settings_get_string
        eplan_settings_list_children
        eplan_status
        eplan_versions
    """),
    "connection_lifecycle": _names("""
        eplan_app_launch
        eplan_app_restart
        eplan_app_shutdown
        eplan_close_pages
        eplan_close_project
        eplan_connect
        eplan_disconnect
        eplan_edit_goto_device
        eplan_edit_open_layout_space
        eplan_edit_open_page
        eplan_navigate_to_eec
        eplan_open_project
        eplan_open_workspace
        eplan_preview_page
        eplan_redraw_ged
        eplan_scratch_project_create
        eplan_scratch_project_discard
        eplan_select_device
        eplan_select_part
    """),
    "arbitrary_execution": _names("""
        eplan_action_run
        eplan_execute_custom_script
        eplan_execute_raw_action
        eplan_execute_script
        eplan_load_api_module
        eplan_load_api_module_net
        eplan_masterdata_operation
        eplan_project_management
        eplan_register_addon
        eplan_register_custom_property_editor
        eplan_register_script
        eplan_run_project_action
        eplan_start_ged_interaction
        eplan_test
        eplan_unregister_addon
        eplan_unregister_script
    """),
    "file_io": _names("""
        aas_export_part
        aas_export_project
        aas_import_parts
        eplan_backup_masterdata
        eplan_backup_project
        eplan_dc_export
        eplan_dc_import
        eplan_export_3d
        eplan_export_connections
        eplan_export_dc_article_data
        eplan_export_device_list
        eplan_export_dwg_pages
        eplan_export_dwg_project
        eplan_export_dxf_pages
        eplan_export_dxf_project
        eplan_export_dxfdwg_pages_scheme
        eplan_export_dxfdwg_project_scheme
        eplan_export_functions
        eplan_export_graphical_layer_table
        eplan_export_graphics_pages
        eplan_export_graphics_project
        eplan_export_location_boxes
        eplan_export_missing_translations
        eplan_export_nc_data
        eplan_export_pages
        eplan_export_parts_list
        eplan_export_pdf_pages
        eplan_export_pdf_project
        eplan_export_pipeline_definitions
        eplan_export_potential_definitions
        eplan_export_production_data_ras_center
        eplan_export_production_data_smart_mounting
        eplan_export_production_wiring
        eplan_export_pxf_project
        eplan_export_ribbon_bar
        eplan_export_segments_template
        eplan_export_settings
        eplan_export_subproject
        eplan_export_to_graphics
        eplan_export_user_properties
        eplan_import_3d
        eplan_import_dc_article_data
        eplan_import_device_list
        eplan_import_dwg_page
        eplan_import_dxf_page
        eplan_import_dxfdwg_files
        eplan_import_graphical_layer_table
        eplan_import_parts_list
        eplan_import_pdf_comments
        eplan_import_preplanning_data
        eplan_import_pxf_project
        eplan_import_ribbon_bar
        eplan_import_segments_template
        eplan_import_settings
        eplan_import_subproject
        eplan_import_user_properties
        eplan_partsmanagement_export
        eplan_partsmanagement_export_all
        eplan_partsmanagement_export_by_properties
        eplan_partsmanagement_import
        eplan_plc_export
        eplan_plc_import
        eplan_print_pages
        eplan_print_project
        eplan_restore_masterdata
        eplan_restore_project
        eplan_save_workspace
    """),
    "project_modification": _names("""
        eplan_calculate_cabinet_weight
        eplan_change_layer
        eplan_check_pages
        eplan_check_parts
        eplan_check_project
        eplan_clean_workspace
        eplan_compress_project
        eplan_convert_base_projects
        eplan_correct_connections
        eplan_create_copper_unfolds
        eplan_create_drilling_views
        eplan_create_graving_text
        eplan_create_installation_space
        eplan_create_labels
        eplan_create_model_views
        eplan_delete_device_list
        eplan_delete_representation_type
        eplan_generate_cables
        eplan_generate_connections
        eplan_generate_macros
        eplan_insert_3d_macro
        eplan_insert_device
        eplan_insert_model_view
        eplan_insert_symbol_reference
        eplan_live_connect_pins
        eplan_live_connect_pins_routed
        eplan_live_create_page
        eplan_live_place_connected
        eplan_live_place_connection_symbol
        eplan_live_place_corner
        eplan_live_place_symbol
        eplan_live_place_tnode
        eplan_live_remove_placement
        eplan_live_set_connection_designations
        eplan_live_set_device_tag
        eplan_live_set_function_text
        eplan_lock_unlock_all_objects
        eplan_parts_db_create
        eplan_parts_db_update
        eplan_prepare_macros
        eplan_remove_language
        eplan_remove_unnecessary_ndps
        eplan_renumber_cables
        eplan_renumber_connections
        eplan_renumber_devices
        eplan_renumber_pages
        eplan_renumber_terminals
        eplan_set_page_property
        eplan_set_parts_data_source
        eplan_set_project_language
        eplan_set_project_property
        eplan_set_project_setting
        eplan_set_property
        eplan_set_setting
        eplan_settings_set_bool
        eplan_settings_set_double
        eplan_settings_set_int
        eplan_settings_set_string
        eplan_switch_project_type
        eplan_synchronize_project
        eplan_topology_operation
        eplan_translate_project
        eplan_unite_net_definition_points
        eplan_update_detail_engineering
        eplan_update_macros
        eplan_update_model_view_pages
        eplan_update_reports
        eplan_update_segments_filling
        eplan_upgrade_projects
    """),
}

# Discovery dispatch can invoke any hidden tool. Lookup itself only reads the
# registry. These are kept separate from the full-mode built-in snapshot.
DISCOVERY_CATEGORIES = {
    "eplan_tools_search": "read_only",
    "eplan_tools_describe": "read_only",
    "eplan_tools_call": "arbitrary_execution",
}

# These are registered by the plugin launcher, after the vendored app is built.
# They become trusted only when the caller explicitly opts them in.
PLUGIN_CATEGORIES = {
    "eplan_doctor": "read_only",
    "eplan_connection_configure": "connection_lifecycle",
    "eplan_documentation_configure": "connection_lifecycle",
}

CATEGORY_BY_NAME = {
    name: category
    for category, names in BUILTIN_CATEGORIES.items()
    for name in names
}
CATEGORY_BY_NAME.update(DISCOVERY_CATEGORIES)

# Unknown/third-party tools cannot become read-only just by reusing a name.
UNKNOWN_CATEGORY = "arbitrary_execution"
META_CATEGORY_KEY = "io.github.shangyunqiang1.eplan-skills/category"


def category_for(name, *, trusted=False):
    """Return a reviewed built-in category, or a conservative default."""
    return CATEGORY_BY_NAME.get(name, UNKNOWN_CATEGORY) if trusted else UNKNOWN_CATEGORY


def annotations_for(category):
    """Return standard MCP hints; these never implement access control."""
    if category not in BUILTIN_CATEGORIES:
        raise ValueError("Unknown EPLAN tool category: %s" % category)
    read_only = category == "read_only"
    return ToolAnnotations(
        readOnlyHint=read_only,
        destructiveHint=not read_only,
        openWorldHint=True,
    )


def policy_options(name, *, trusted=False):
    category = category_for(name, trusted=trusted)
    return {
        "annotations": annotations_for(category),
        "meta": {META_CATEGORY_KEY: category},
    }
