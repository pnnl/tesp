import sys
import tesp_support.feederGenerator as fg;

fp = open('houses.glm', 'w')

phs='ABC'
region=2
xfkva=1000.0
xfkvll=13.2
electric_cooling_fraction=0.8
solar_fraction=0.0
storage_fraction=0.0
split_secondary=False

fg.write_node_houses (fp, node='F7B1', nh=42, write_configs=True, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F7B2', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F7B3', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F7B4', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F7B5', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F7B6', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F7B7', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F7B8', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F1B1', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F1B2', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F1B3', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F1B4', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F1B5', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)
fg.write_node_houses (fp, node='F1B6', nh=42, write_configs=False, phs=phs, region=region, xfkva=xfkva, xfkvll=xfkvll, electric_cooling_fraction=electric_cooling_fraction, solar_fraction=solar_fraction, storage_fraction=storage_fraction, split_secondary=split_secondary)

fp.close()
