# Licenses and source attribution

The study software is licensed under MIT. Original documentation and author-created data are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Source products and their derivative subsets retain the terms below. Paths beginning with `work/` refer to the extracted reproduction code directory; they are not directories inside the standalone supplement.

## Sentinel-2 observations

The spectra and observation arrays contain modified Copernicus Sentinel data from 2017–2024, processed by INPE/Brazil Data Cube as S2-16D-2 and extracted at eligible study positions. The [S2-16D-2 collection](https://data.inpe.br/bdc/stac/v1/collections/S2-16D-2) records the STAC license value `proprietary` and links the [Copernicus Sentinel legal notice](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice). That notice permits reproduction, distribution and adaptation with source attribution. The source metadata retain this license information; the study's CC BY 4.0 statement does not replace it.

## TerraClass thematic data

The cropped TerraClass rasters for 2016, 2018, 2020, 2022 and 2024 and their derived permanence/core masks are distributed under [CC BY-SA 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/). Attribution is to TerraClass/INPE/Embrapa. Their transformations comprise cropping, geometric alignment where recorded, nearest-neighbour reprojection and thematic erosion. The [official metadata record for the 2020 raster](https://terrabrasilis.dpi.inpe.br/geonetwork/srv/api/records/f49a47f8-12ae-4052-8e0d-2e581458dc69/formatters/xml) also specifies CC BY-SA 4.0.

The spatial manifest retains the hash of the aligned 2024 input and identifies its alignment history from the local filename. The original transformation record was not available. The archived file is the reproduction input.

## Basin geometry

`work/basin.gpkg` contains the selected ANA/SNIRH ottobasin from BHO Multiscale 2017. The spatial manifest records the source version and transformations. The [SNIRH data portal](https://www.snirh.gov.br/cnarh40) describes public access to its open datasets. The study asserts no additional copyright over the source geometry.

## Official TerraClass services

The [WMS capabilities](https://www.terraclass.gov.br/geoserver/wms?service=WMS&request=GetCapabilities&version=1.3.0) list the rendered map layers `TerraClass:tc_amazonia_YYYY_raster`. The [WCS capabilities](https://www.terraclass.gov.br/geoserver/wcs?service=WCS&request=GetCapabilities&version=2.0.1) list raster coverages, including `TerraClass__tc_amazonia_2024_raster`. Both include the five study years.

The service describes the 2024 coverage in EPSG:3857 with spacing of about 10.057 m. This is a current access service; the locally aligned input and archived thematic windows are identified separately by their hashes and grid metadata.
