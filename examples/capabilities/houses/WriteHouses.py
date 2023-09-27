# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: WriteHouses.py

import tesp_support.original.residential_feeder_glm as fg

fp = open('houses.glm', 'w')

xfkva3 = 1000.0
xfkva1 = 500.0
xfkvll = 13.2
xfkvln = 7.621

fg.write_node_house_configs(fp, xfkva3, xfkvll, xfkvln, phs='ABC', want_inverter=True)
fg.write_node_house_configs(fp, xfkva1, xfkvll, xfkvln, phs='ABCS')

fg.write_node_houses(fp, node='F7B1', nh=42, xfkva=xfkva3, phs='ABC', region=2,
                     electric_cooling_fraction=0.8, solar_fraction=0.0, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F7B2', nh=42, xfkva=xfkva1, phs='AS', region=2,
                     electric_cooling_fraction=0.8, solar_fraction=0.0, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F7B3', nh=42, xfkva=xfkva1, phs='BS', region=2,
                     electric_cooling_fraction=0.8, solar_fraction=0.0, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F7B4', nh=42, xfkva=xfkva1, phs='CS', region=2,
                     electric_cooling_fraction=0.8, solar_fraction=0.0, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F7B5', nh=42, xfkva=xfkva1, phs='AS', region=2, secondary_ft=75.0,
                     electric_cooling_fraction=0.8, solar_fraction=0.0, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F7B6', nh=42, xfkva=xfkva1, phs='BS', region=2, secondary_ft=75.0,
                     electric_cooling_fraction=0.8, solar_fraction=0.5, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F7B7', nh=42, xfkva=xfkva1, phs='CS', region=2, secondary_ft=75.0,
                     electric_cooling_fraction=0.8, solar_fraction=0.5, storage_fraction=0.5, node_metrics_interval=300)
fg.write_node_houses(fp, node='F7B8', loadkw=0.8 * xfkva3, house_avg_kw=20.0, xfkva=xfkva3, phs='ABC', region=2,
                     electric_cooling_fraction=0.8, solar_fraction=0.0, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F1B1', nh=42, xfkva=xfkva3, phs='ABC', region=1,
                     electric_cooling_fraction=0.8, solar_fraction=0.0, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F1B2', nh=42, xfkva=xfkva3, phs='ABC', region=3,
                     electric_cooling_fraction=0.8, solar_fraction=0.0, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F1B3', nh=42, xfkva=xfkva3, phs='ABC', region=4,
                     electric_cooling_fraction=0.8, solar_fraction=0.0, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F1B4', nh=42, xfkva=xfkva3, phs='ABC', region=5,
                     electric_cooling_fraction=0.8, solar_fraction=0.0, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F1B5', nh=42, xfkva=xfkva3, phs='ABC', region=2, secondary_ft=75.0,
                     electric_cooling_fraction=0.8, solar_fraction=0.0, storage_fraction=0.0, node_metrics_interval=300)
fg.write_node_houses(fp, node='F1B6', nh=42, xfkva=xfkva3, phs='ABC', region=2,
                     electric_cooling_fraction=0.8, solar_fraction=0.5, storage_fraction=0.5, node_metrics_interval=300)

fp.close()
