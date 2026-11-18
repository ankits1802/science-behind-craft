from dataclasses import asdict, dataclass

CLIMATE_FIRST_YEAR = 1981


@dataclass(frozen=True)
class Dataset:
    code: str
    title: str
    publisher: str
    edition: str
    period: str
    nativeResolution: str
    crs: str
    licence: str
    licenceUrl: str | None
    attribution: str
    redistributable: bool
    citation: str | None
    url: str

    def as_row(self) -> dict:
        return asdict(self)


BOUNDARIES = Dataset(
    code="DR_DISTRICT_SHAPES",
    title="Indian district boundaries, matched to LGD codes",
    publisher="Indian districts GeoJSON on Kaggle",
    edition="2026",
    period="2026",
    nativeResolution="simplified to 0.01 degree, 0.001 degree coordinate grid",
    crs="EPSG:4326",
    licence="For reference only",
    licenceUrl=None,
    attribution="District boundaries are indicative.",
    redistributable=False,
    citation=None,
    url="https://www.kaggle.com/datasets/adityaradha007/indian-districts-geojson",
)

SOILGRIDS = Dataset(
    code="SOILGRIDS_2_0",
    title="SoilGrids 2.0",
    publisher="ISRIC World Soil Information",
    edition="2.0",
    period="modelled, 2020 release",
    nativeResolution="250 m",
    crs="Interrupted Goode Homolosine (ESRI:54052)",
    licence="CC BY 4.0",
    licenceUrl="https://creativecommons.org/licenses/by/4.0/",
    attribution="SoilGrids 2.0, ISRIC World Soil Information",
    redistributable=True,
    citation=(
        "Poggio, L., de Sousa, L. M., Batjes, N. H., et al. (2021). SoilGrids 2.0: producing soil information "
        "for the globe with quantified spatial uncertainty. SOIL 7, 217-240. https://doi.org/10.5194/soil-7-217-2021"
    ),
    url="https://files.isric.org/soilgrids/latest/data/",
)

WORLDCOVER = Dataset(
    code="ESA_WORLDCOVER_2021_V200",
    title="ESA WorldCover 10 m 2021 v200",
    publisher="European Space Agency",
    edition="v200",
    period="2021",
    nativeResolution="10 m (1/12000 degree)",
    crs="EPSG:4326",
    licence="CC BY 4.0",
    licenceUrl="https://creativecommons.org/licenses/by/4.0/",
    attribution=(
        "ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) "
        "processed by ESA WorldCover consortium"
    ),
    redistributable=True,
    citation=(
        "Zanaga, D., Van De Kerchove, R., Daems, D., et al. (2022). ESA WorldCover 10 m 2021 v200. "
        "https://doi.org/10.5281/zenodo.7254221"
    ),
    url="https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/",
)

HANSEN = Dataset(
    code="HANSEN_GFC_2025_V1_13",
    title="Global Forest Change 2000-2025",
    publisher="University of Maryland, Department of Geographical Sciences",
    edition="GFC-2025-v1.13",
    period="2000-2025",
    nativeResolution="1 arc-second (about 30 m)",
    crs="EPSG:4326",
    licence="CC BY 4.0",
    licenceUrl="https://creativecommons.org/licenses/by/4.0/",
    attribution="Hansen/UMD/Google/USGS/NASA",
    redistributable=True,
    citation=(
        "Hansen, M. C., Potapov, P. V., Moore, R., et al. (2013). High-Resolution Global Maps of 21st-Century "
        "Forest Cover Change. Science 342, 850-853. https://doi.org/10.1126/science.1244693. Data GFC-2025-v1.13."
    ),
    url="https://storage.googleapis.com/earthenginepartners-hansen/GFC-2025-v1.13/",
)

CHELSA = Dataset(
    code="CHELSA_2_1_1981_2010",
    title="CHELSA V2.1 climatologies 1981-2010",
    publisher="Swiss Federal Institute for Forest, Snow and Landscape Research WSL",
    edition="V2.1",
    period="1981-2010",
    nativeResolution="30 arc-seconds (about 1 km)",
    crs="EPSG:4326",
    licence="Karger et al. 2017",
    licenceUrl="https://doi.org/10.1038/sdata.2017.122",
    attribution="CHELSA V2.1",
    redistributable=False,
    citation=(
        "Karger, D. N., Conrad, O., Bohner, J., et al. (2017). Climatologies at high resolution for the earth's "
        "land surface areas. Scientific Data 4, 170122. https://doi.org/10.1038/sdata.2017.122"
    ),
    url="https://os.zhdk.cloud.switch.ch/chelsav2/GLOBAL/climatologies/1981-2010/",
)

CHIRPS = Dataset(
    code="CHIRPS_3_0",
    title="Climate Hazards Center InfraRed Precipitation with Stations v3.0",
    publisher="Climate Hazards Center, UC Santa Barbara",
    edition="3.0",
    period="set per run",
    nativeResolution="0.05 degree",
    crs="EPSG:4326",
    licence="CC BY 4.0",
    licenceUrl="https://creativecommons.org/licenses/by/4.0/",
    attribution="Climate Hazards Center, UC Santa Barbara (CHIRPS3)",
    redistributable=True,
    citation=(
        "Climate Hazards Center InfraRed Precipitation with Stations version 3 (CHIRPS3) Data Repository (2025). "
        "https://doi.org/10.15780/G2JQ0P"
    ),
    url="https://data.chc.ucsb.edu/products/CHIRPS/v3.0/",
)

GHCN_CAMS = Dataset(
    code="GHCN_CAMS_T2M",
    title="GHCN CAMS gridded monthly land surface air temperature",
    publisher="NOAA Climate Prediction Center, distributed by NOAA Physical Sciences Laboratory",
    edition="air.mon.mean.nc, file version 3.01",
    period="set per run",
    nativeResolution="0.5 degree",
    crs="EPSG:4326",
    licence="Public domain (U.S. Government work on a federal server)",
    licenceUrl="https://psl.noaa.gov/data/help/",
    attribution="GHCN_CAMS Gridded 2m Temperature (Land) data provided by the NOAA PSL, Boulder, Colorado, USA",
    redistributable=True,
    citation=(
        "Fan, Y., van den Dool, H. (2008). A global monthly land surface air temperature analysis for "
        "1948-present. Journal of Geophysical Research 113, D01103. https://doi.org/10.1029/2007JD008470"
    ),
    url="https://downloads.psl.noaa.gov/Datasets/ghcncams/air.mon.mean.nc",
)

COPDEM = Dataset(
    code="COPERNICUS_DEM_GLO90",
    title="Copernicus DEM GLO-90",
    publisher="European Space Agency, Copernicus Programme",
    edition="2021_1 (AWS Open Data COG)",
    period="2011-2015 acquisitions",
    nativeResolution="3 arc-seconds (about 90 m)",
    crs="EPSG:4326 (EGM2008 heights)",
    licence="Copernicus DEM licence (GLO-90 free worldwide)",
    licenceUrl="https://registry.opendata.aws/copernicus-dem/",
    attribution=(
        "Produced using Copernicus WorldDEM-90 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH "
        "2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved"
    ),
    redistributable=True,
    citation="European Space Agency (2024). Copernicus Global Digital Elevation Model. https://doi.org/10.5270/ESA-c5d3d65",
    url="https://copernicus-dem-90m.s3.amazonaws.com/",
)

HYDRORIVERS = Dataset(
    code="HYDRORIVERS_1_0",
    title="HydroRIVERS v1.0 (Asia)",
    publisher="WWF HydroSHEDS",
    edition="v10",
    period="static",
    nativeResolution="15 arc-second network (reaches with upstream area >= 10 km2 or discharge >= 0.1 m3/s)",
    crs="EPSG:4326",
    licence=(
        "HydroSHEDS v1 License Agreement: free for non-commercial and commercial use; distributed only inside "
        "derived products, never on its own; attribution required"
    ),
    licenceUrl="https://data.hydrosheds.org/file/technical-documentation/HydroSHEDS_TechDoc_v1_4.pdf",
    attribution=(
        "This product KalaVigyan incorporates data from the HydroSHEDS version 1 database which is © World "
        "Wildlife Fund, Inc. (2006-2022) and has been used herein under license. WWF has not evaluated the data as "
        "altered and incorporated within KalaVigyan, and therefore gives no warranty regarding its accuracy, "
        "completeness, currency or suitability for any particular purpose. Portions of the HydroSHEDS v1 database "
        "incorporate data which are the intellectual property rights of © USGS (2006-2008), NASA (2000-2005), "
        "ESRI (1992-1998), CIAT (2004-2006), UNEP-WCMC (1993), WWF (2004), Commonwealth of Australia (2007), and "
        "Her Royal Majesty and the British Crown and are used under license. The HydroSHEDS v1 database and more "
        "information are available at https://www.hydrosheds.org."
    ),
    redistributable=True,
    citation=(
        "Lehner, B., Grill, G. (2013). Global river hydrography and network routing: baseline data and new "
        "approaches to study the world's large river systems. Hydrological Processes 27(15), 2171-2186. "
        "https://doi.org/10.1002/hyp.9740"
    ),
    url="https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_as_shp.zip",
)

MRDS = Dataset(
    code="USGS_MRDS",
    title="Mineral Resources Data System",
    publisher="U.S. Geological Survey",
    edition="WFS snapshot at retrieval",
    period="compiled to 2011, no longer updated",
    nativeResolution="point locations",
    crs="EPSG:4326",
    licence="Public domain (U.S. Government work)",
    licenceUrl="https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
    attribution="U.S. Geological Survey Mineral Resources Data System",
    redistributable=True,
    citation="U.S. Geological Survey. Mineral Resources Data System (MRDS). Reston, Virginia. https://mrdata.usgs.gov/mrds/",
    url="https://mrdata.usgs.gov/services/wfs/mrds",
)

GLIM = Dataset(
    code="GLIM_1_0_05DEG",
    title="Global Lithological Map Database v1.0 (gridded to 0.5 degree)",
    publisher="Universitat Hamburg, via PANGAEA",
    edition="1.0",
    period="2012",
    nativeResolution="0.5 degree",
    crs="EPSG:4326",
    licence="CC BY 3.0",
    licenceUrl="https://creativecommons.org/licenses/by/3.0/",
    attribution="Hartmann and Moosdorf (2012), GLiM",
    redistributable=True,
    citation=(
        "Hartmann, J., Moosdorf, N. (2012). Global Lithological Map Database v1.0 (gridded to 0.5 degree spatial "
        "resolution). PANGAEA. https://doi.org/10.1594/PANGAEA.788537"
    ),
    url="https://doi.pangaea.de/10.1594/PANGAEA.788537?format=textfile",
)

ALL = {
    d.code: d
    for d in (BOUNDARIES, SOILGRIDS, WORLDCOVER, HANSEN, CHELSA, CHIRPS, GHCN_CAMS, COPDEM, HYDRORIVERS, MRDS, GLIM)
}
