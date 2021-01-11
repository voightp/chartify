# def test_change_model(tree_view: TreeView):
#     tree_view.change_model("daily")
#     assert tree_view.source_model.name == "daily"
#     assert tree_view.source_model.energy_units == "J"
#     assert tree_view.source_model.rate_units == "W"
#     assert tree_view.source_model.units_system == "SI"
#     assert not tree_view.source_model.rate_to_energy
#     assert tree_view.source_model.tree_node == "type"
#
#
# def test_set_and_update_model(tree_view: TreeView):
#     units = {
#         "energy_units": "J",
#         "rate_units": "MW",
#         "rate_to_energy": True,
#         "units_system": "IP",
#     }
#     tree_view.set_model("daily", tree_node="key", **units)
#     assert tree_view.source_model.name == "daily"
#     assert tree_view.source_model.energy_units == "J"
#     assert tree_view.source_model.rate_units == "MW"
#     assert tree_view.source_model.units_system == "IP"
#     assert tree_view.source_model.rate_to_energy
#     assert tree_view.source_model.tree_node == "key"
