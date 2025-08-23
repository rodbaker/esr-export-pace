USDA’s **Foreign Agricultural Service data API portal** provides users the ability to obtain programmatic access to publicly available agricultural commodity data from the Export Sales Report (ESR) databases.

**FACT SHEET: USDA's Export Sales Reporting Program:** 

Provides Markets with an Early Alert USDA's Export Sales Reporting Program monitors U.S. agricultural export sales on a daily and weekly basis. Export sales reporting provides a constant stream of up-to-date market information for 40 U.S. agricultural commodities sold abroad. A single statistic reveals the significance of the program: in a typical year, the program monitors more than 40 percent of total U.S. agricultural exports. The program also serves as an early alert on the possible impact foreign sales have on U.S. supplies and prices. The weekly U.S. Export Sales report is the most current available source of U.S. export sales data. The data is used to analyze the overall level of export demand, determine where markets exist, and assess the relative position of U.S. commodities in foreign markets. Why the Program was Created The Export Sales Reporting Program has its roots from the unexpected purchase of large amounts of grain by the Soviet Union in 1972, “The Great Russian Grain Robbery”. The huge, unanticipated purchases of U.S. wheat and corn that year depleted U.S. reserve stocks which caused a sizable run-up in U.S. food prices. Furthermore, there was growing concern that some companies might have an unfair advantage in situations like this because they had access to market-sensitive information that was unavailable to the public. To ensure that all parties involved in the production and export of U.S. grain had access to up-to-date export sales information, Congress mandated the Export Sales Reporting program in 1973\. Before the program was established, it was difficult for the public to obtain information on export sales until the products were actually shipped. The program helps facilitate price stability by guaranteeing that everyone has access to the same information at the same time. How the Program Works The program requires both daily and weekly reporting of export sales. Weekly reporting is required for certain reportable commodities including: feed grains, wheat, wheat products, rye, flaxseed, linseed oil, cotton, cottonseed, oilseeds and products, rice, cattle hides and skins, beef, and pork. U.S. exporters are also required to report all large sales activity made in a single day to a single country for certain commodities by 3:00 p.m. Eastern time on the business day after a sale is made. Large export sales of certain commodities are defined as 100,000 metric tons (20,000 tons for soybean oil) or more of one commodity in one day to a single destination, or cumulative sales of 200,000 tons (40,000 tons for soybean oil) or more of one commodity during the weekly reporting period to a single destination. The commodities covered by the Export Sales Reporting Program have been selected for monitoring by Congressional action or through consultations between USDA and organizations that represent commodity producers and traders. The Secretary of Agriculture has the authority to add any commodity that the Secretary wishes to the list of commodities that are monitored. U.S. exporters provide information on the quantity of their sales transactions, the type and class of commodity, the marketing year of the shipment, and the ultimate destination. They also report any changes to previously reported information, such as cancellations or changes in destinations. About 370 exporters report on a weekly basis via online, fax, or e-mail, with approximately 1,300 data entries each week. All data remains confidential, as required by law, and is released only in aggregate form. Checks and Balances Several measures ensure the accuracy of the information. FAS has memorandum of understandings with USDA's Grain Inspection, Packers and Stockyards Administration, as well as with the U.S. Bureau of the Census to share data and resolve discrepancies that exist. Staff members meet periodically with exporters to verify and reinforce sound reporting practices. As an additional check, exporters must submit quarterly contract information reports that help to confirm reported activities. Contact Information For more information on the Export Sales Reporting Program, please contact the Export Sales Reporting staff at: Tel.: (202) 720-9209 Fax: (202) 690-3270 E-mail: esr@fas.usda.gov Accessing the Information Daily Sales: Daily sales are required to be reported to USDA by 3:00 p.m. on the day after the sales are made, and are then summarized and released to the public at 9:00 a.m. on the next business day. Daily sales news releases are available on the FAS web site at: http://www.fas.usda.gov/programs/export-sales-reportingprogram Weekly Report: The weekly report of export sales activity, “U.S. Export Sales”, is published every Thursday at 8:30 a.m. eastern time. The export sales report is available on the FAS Web site at: www.fas.usda.gov/exportsales/esrd1.asp The “U.S. Export Sales” report is also available in paper copy via annual subscription from the National Technical Information Service: Tel.: 1-800-553-NTIS or customerservice@ntis.gov Historical Data: Detailed historical data is available through the Export Sales Query System at: http://apps.fas.usda.gov/esrquery/ GovDelivery: Users can receive an email copy of the weekly export sales report, daily sales releases, as well as other USDA reports and releases through GovDelivery. Enter your email address at [http://www.fas.usda.gov](http://www.fas.usda.gov)

[ESR Data API \- United States Weekly Export Sales of Agricultural Commodity Data](https://apps.fas.usda.gov/opendatawebV2/#/ESR%20Data%20API%20-%20United%20States%20Weekly%20Export%20Sales%20of%20Agricultural%20Commodity%20Data)

[​/api​/esr​/regions](https://apps.fas.usda.gov/opendatawebV2/#/ESR%20Data%20API%20-%20United%20States%20Weekly%20Export%20Sales%20of%20Agricultural%20Commodity%20Data/ESRData_GetRegions)  
Returns a set of records with Region Codes and Region Names. Use it to associate Region Name with Country records obtained by querying Country end point

Request url:  
https://api.fas.usda.gov/api/esr/regions

Response body  
\[  
  {  
    "regionId": 1,  
    "regionName": "EUROPEAN UNION \- 27           "  
  },  
  {  
    "regionId": 2,  
    "regionName": "OTHER EUROPE                  "  
  },  
  {  
    "regionId": 3,  
    "regionName": "EASTERN EUROPE                "  
  },  
  {  
    "regionId": 4,  
    "regionName": "FORMER SOVIET UNION-12        "  
  },  
  {  
    "regionId": 5,  
    "regionName": "JAPAN                         "  
  },  
  {  
    "regionId": 6,  
    "regionName": "TAIWAN                        "  
  },  
  {  
    "regionId": 7,  
    "regionName": "CHINA                         "  
  },  
  {  
    "regionId": 8,  
    "regionName": "INDIA                         "  
  },  
  {  
    "regionId": 9,  
    "regionName": "OTHER ASIA AND OCEANIA        "  
  },  
  {  
    "regionId": 10,  
    "regionName": "AFRICA                        "  
  },  
  {  
    "regionId": 11,  
    "regionName": "WESTERN HEMISPHERE            "  
  },  
  {  
    "regionId": 99,  
    "regionName": "UNKNOWN                       "  
  }  
\]

/api/esr/countries

Returns a set of records with Countries and their corresponding Regions Codes the Country belongs to. Use it to associate Country Name with Commodity Data records obtained by querying Commodity Data End point

Request url:

https://api.fas.usda.gov/api/esr/countries

Response body

\[

  {

    "countryCode": 1,

    "countryName": "EUROPEAN",

    "countryDescription": "EUROPEAN UNION \- 27           ",

    "regionId": 1,

    "gencCode": null

  },

  {

    "countryCode": 2,

    "countryName": "UNKNOWN",

    "countryDescription": "UNKNOWN",

    "regionId": 99,

    "gencCode": "AX1"

  },

  {

    "countryCode": 1010,

    "countryName": "GREENLD ",

    "countryDescription": "GREENLAND                      ",

    "regionId": 11,

    "gencCode": "GRL"

  },

  {

    "countryCode": 1220,

    "countryName": "CANADA  ",

    "countryDescription": "CANADA                         ",

    "regionId": 11,

    "gencCode": "CAN"

  },

  {

    "countryCode": 1610,

    "countryName": "MIGUEL  ",

    "countryDescription": "ST. PIERRE AND MIQUELON        ",

    "regionId": 11,

    "gencCode": null

  },

  {

    "countryCode": 2010,

    "countryName": "MEXICO  ",

    "countryDescription": "MEXICO                         ",

    "regionId": 11,

    "gencCode": "MEX"

  },

  {

    "countryCode": 2050,

    "countryName": "GUATMAL ",

    "countryDescription": "GUATEMALA                      ",

    "regionId": 11,

    "gencCode": "GTM"

  },

  {

    "countryCode": 2080,

    "countryName": "BELIZE  ",

    "countryDescription": "BELIZE                         ",

    "regionId": 11,

    "gencCode": "BLZ"

  },

  {

    "countryCode": 2110,

    "countryName": "SALVADR ",

    "countryDescription": "EL SALVADOR                    ",

    "regionId": 11,

    "gencCode": "SLV"

  },

  {

    "countryCode": 2150,

    "countryName": "HONDURA ",

    "countryDescription": "HONDURAS                       ",

    "regionId": 11,

    "gencCode": "HND"

  },

  {

    "countryCode": 2190,

    "countryName": "NICARAG ",

    "countryDescription": "NICARAGUA                      ",

    "regionId": 11,

    "gencCode": "NIC"

  },

  {

    "countryCode": 2230,

    "countryName": "C RICA  ",

    "countryDescription": "COSTA RICA                     ",

    "regionId": 11,

    "gencCode": "CRI"

  },

  {

    "countryCode": 2250,

    "countryName": "PANAMA  ",

    "countryDescription": "PANAMA                         ",

    "regionId": 11,

    "gencCode": "PAN"

  },

  {

    "countryCode": 2270,

    "countryName": "CANAL Z ",

    "countryDescription": "PANAMA CANAL ZONE              ",

    "regionId": 11,

    "gencCode": null

  },

  {

    "countryCode": 2320,

    "countryName": "BERMUDA ",

    "countryDescription": "BERMUDA                        ",

    "regionId": 11,

    "gencCode": "BMU"

  },

Request url

​/api​/esr​/commodities

Returns a set of records with Commodity Information. Use it to associate Commodity Name with Commodity Data records obtained by querying Commodity Data End point

Response body

\[

  {

    "commodityCode": 101,

    "commodityName": "Wheat \- HRW",

    "unitId": 1

  },

  {

    "commodityCode": 102,

    "commodityName": "Wheat \- SRW",

    "unitId": 1

  },

  {

    "commodityCode": 103,

    "commodityName": "Wheat \- HRS",

    "unitId": 1

  },

  {

    "commodityCode": 104,

    "commodityName": "Wheat \- White",

    "unitId": 1

  },

  {

    "commodityCode": 105,

    "commodityName": "Wheat \- Durum",

    "unitId": 1

  },

  {

    "commodityCode": 106,

    "commodityName": "Wheat \- Mixed",

    "unitId": 1

  },

  {

    "commodityCode": 107,

    "commodityName": "All Wheat",

    "unitId": 1

  },

  {

    "commodityCode": 201,

    "commodityName": "Wheat Products",

    "unitId": 1

  },

Request url:

https://api.fas.usda.gov/api/esr/unitsOfMeasure

Returns a set of records with Units of Measure Information. Use it to associate Unit Of Measure Name with Commodity Data records obtained by querying Commodity Data End point

Response body

\[

  {

    "unitId": 1,

    "unitNames": "Metric Tons"

  },

  {

    "unitId": 2,

    "unitNames": "Running Bales"

  },

  {

    "unitId": 3,

    "unitNames": "Pieces"

  },

  {

    "unitId": 4,

    "unitNames": "NUMBER"

  },

  {

    "unitId": 5,

    "unitNames": "Pounds"

  }

\]

[​/api​/esr​/datareleasedates](https://apps.fas.usda.gov/opendatawebV2/#/ESR%20Data%20API%20-%20United%20States%20Weekly%20Export%20Sales%20of%20Agricultural%20Commodity%20Data/ESRData_GetDataReleaseInfo)

Returns a set of records with the date of the last release of ESR Commodity Export Data. Please note that there could be revision on the Export numbers for multiple years on a given commodity, and so this API endpoint returns set of records containing data release dates at a commodity level Use this information to query for only the Export data that has changed since last invocation of this API End point

Request URL

https://api.fas.usda.gov/api/esr/datareleasedates

Response body:

\[

  {

    "commodityCode": 101,

    "marketYearStart": "2025-06-01T00:00:00",

    "marketYearEnd": "2026-05-31T00:00:00",

    "marketYear": 2026,

    "releaseTimeStamp": "2025-08-14T00:00:00"

  },

  {

    "commodityCode": 102,

    "marketYearStart": "2025-06-01T00:00:00",

    "marketYearEnd": "2026-05-31T00:00:00",

    "marketYear": 2026,

    "releaseTimeStamp": "2025-08-14T00:00:00"

  },

  {

    "commodityCode": 103,

    "marketYearStart": "2025-06-01T00:00:00",

    "marketYearEnd": "2026-05-31T00:00:00",

    "marketYear": 2026,

    "releaseTimeStamp": "2025-08-14T00:00:00"

  },

  {

    "commodityCode": 104,

    "marketYearStart": "2025-06-01T00:00:00",

    "marketYearEnd": "2026-05-31T00:00:00",

    "marketYear": 2026,

    "releaseTimeStamp": "2025-08-14T00:00:00"

  },

  {

    "commodityCode": 105,

    "marketYearStart": "2025-06-01T00:00:00",

    "marketYearEnd": "2026-05-31T00:00:00",

    "marketYear": 2026,

    "releaseTimeStamp": "2025-08-14T00:00:00"

  },

  {

    "commodityCode": 107,

    "marketYearStart": "2025-06-01T00:00:00",

    "marketYearEnd": "2026-05-31T00:00:00",

    "marketYear": 2026,

    "releaseTimeStamp": "2025-08-14T00:00:00"

  },

/api/esr/exports/commodityCode/{commodityCode}/allCountries/marketYear/{marketYear}

Given Commodity Code (Ex: 104 for Wheat \- White ) and MarketYear (Ex: 2017\) this API End point will return a list of US Export records of White Wheat to all applicable countries from USA for the given Market Year. Please see DataReleaseDates end point to get a list of all Commodities and the corresponding Market Year data.

Request URL

https://api.fas.usda.gov/api/esr/exports/commodityCode/104/allCountries/marketYear/2024

Response body

\[

  {

    "commodityCode": 104,

    "countryCode": 1220,

    "weeklyExports": 0,

    "accumulatedExports": 0,

    "outstandingSales": 311,

    "grossNewSales": 311,

    "currentMYNetSales": 0,

    "currentMYTotalCommitment": 311,

    "nextMYOutstandingSales": 0,

    "nextMYNetSales": 0,

    "unitId": 1,

    "weekEndingDate": "2023-06-01T00:00:00"

  },

  {

    "commodityCode": 104,

    "countryCode": 5210,

    "weeklyExports": 0,

    "accumulatedExports": 0,

    "outstandingSales": 50000,

    "grossNewSales": 50000,

    "currentMYNetSales": 0,

    "currentMYTotalCommitment": 50000,

    "nextMYOutstandingSales": 0,

    "nextMYNetSales": 0,

    "unitId": 1,

    "weekEndingDate": "2023-06-01T00:00:00"

  },

  {

    "commodityCode": 104,

    "countryCode": 5420,

    "weeklyExports": 19800,

    "accumulatedExports": 19800,

    "outstandingSales": 0,

    "grossNewSales": 0,

    "currentMYNetSales": 19800,

    "currentMYTotalCommitment": 19800,

    "nextMYOutstandingSales": 0,

    "nextMYNetSales": 0,

    "unitId": 1,

    "weekEndingDate": "2023-06-01T00:00:00"

  },

  {

    "commodityCode": 104,

    "countryCode": 5490,

    "weeklyExports": 0,

    "accumulatedExports": 0,

    "outstandingSales": 19357,

    "grossNewSales": 357,

    "currentMYNetSales": 0,

    "currentMYTotalCommitment": 19357,

    "nextMYOutstandingSales": 0,

    "nextMYNetSales": 0,

    "unitId": 1,

    "weekEndingDate": "2023-06-01T00:00:00"

  },

  {

    "commodityCode": 104,

    "countryCode": 5520,

    "weeklyExports": 0,

    "accumulatedExports": 0,

    "outstandingSales": 12000,

    "grossNewSales": 0,

    "currentMYNetSales": 0,

    "currentMYTotalCommitment": 12000,

    "nextMYOutstandingSales": 0,

    "nextMYNetSales": 0,

    "unitId": 1,

    "weekEndingDate": "2023-06-01T00:00:00"

  },

[​/api​/esr​/exports​/commodityCode​/{commodityCode}​/countryCode​/{countryCode}​/marketYear​/{marketYear}](https://apps.fas.usda.gov/opendatawebV2/#/ESR%20Data%20API%20-%20United%20States%20Weekly%20Export%20Sales%20of%20Agricultural%20Commodity%20Data/ESRData_GetCountryData)

Given Commodity Code (Ex: 104 for Wheat \- White ), Country Code (Ex:1220 for Canada) and MarketYear (Ex: 2017\) this API End point will return a list of US Export records of White Wheat to Canada from USA for the give Market Year. Please see DataReleaseDates end point to get a list of all Commodities and the corresponding Market Year data

Request URL:

https://api.fas.usda.gov/api/esr/exports/commodityCode/104/countryCode/1220/marketYear/2024

Response body

\[

  {

    "commodityCode": 104,

    "countryCode": 1220,

    "weeklyExports": 0,

    "accumulatedExports": 0,

    "outstandingSales": 311,

    "grossNewSales": 311,

    "currentMYNetSales": 0,

    "currentMYTotalCommitment": 311,

    "nextMYOutstandingSales": 0,

    "nextMYNetSales": 0,

    "unitId": 1,

    "weekEndingDate": "2023-06-01T00:00:00"

  },

  {

    "commodityCode": 104,

    "countryCode": 1220,

    "weeklyExports": 200,

    "accumulatedExports": 200,

    "outstandingSales": 791,

    "grossNewSales": 680,

    "currentMYNetSales": 680,

    "currentMYTotalCommitment": 991,

    "nextMYOutstandingSales": 0,

    "nextMYNetSales": 0,

    "unitId": 1,

    "weekEndingDate": "2023-06-08T00:00:00"

  },

  {

    "commodityCode": 104,

    "countryCode": 1220,

    "weeklyExports": 284,

    "accumulatedExports": 484,

    "outstandingSales": 652,

    "grossNewSales": 145,

    "currentMYNetSales": 145,

    "currentMYTotalCommitment": 1136,

    "nextMYOutstandingSales": 0,

    "nextMYNetSales": 0,

    "unitId": 1,

    "weekEndingDate": "2023-06-15T00:00:00"

  },

  {

    "commodityCode": 104,

    "countryCode": 1220,

    "weeklyExports": 112,

    "accumulatedExports": 596,

    "outstandingSales": 540,

    "grossNewSales": 0,

    "currentMYNetSales": 0,

    "currentMYTotalCommitment": 1136,

    "nextMYOutstandingSales": 0,

    "nextMYNetSales": 0,

    "unitId": 1,

    "weekEndingDate": "2023-06-22T00:00:00"

  },

  {

    "commodityCode": 104,

    "countryCode": 1220,

    "weeklyExports": 227,

    "accumulatedExports": 823,

    "outstandingSales": 313,

    "grossNewSales": 0,

    "currentMYNetSales": 0,

    "currentMYTotalCommitment": 1136,

    "nextMYOutstandingSales": 0,

    "nextMYNetSales": 0,

    "unitId": 1,

    "weekEndingDate": "2023-06-29T00:00:00"

  },

  {

    "commodityCode": 104,

    "countryCode": 1220,

    "weeklyExports": 0,

    "accumulatedExports": 823,

    "outstandingSales": 313,

    "grossNewSales": 0,

    "currentMYNetSales": 0,

    "currentMYTotalCommitment": 1136,

    "nextMYOutstandingSales": 0,

    "nextMYNetSales": 0,

    "unitId": 1,

    "weekEndingDate": "2023-07-06T00:00:00"

  },

Definitions for ESR Query

| Weekly Exports \- Shipments of reportable commodities exported against sales for a reporting week Friday through Thursday. |
| ----- |
| **Accumulated Exports** \- Accumulated shipments of reportable commodities from the beginning of the marketing year (for each commodity) to the current week ending date. \* Note:Accumulated exports are revised periodically due to adjustments made by reporting exporters. |
| **Outstanding Sales** \- The total outstanding export sales contracts by country and/or commodity that have not been shipped at any given time during the marketing year. |
| **Gross New Sales** \- Includes increases resulting from new export sales, contract adjustments, loading tolerances, changes in marketing year, change in commodity or sales made against exports for the exporter's own account. Note: Gross new sales will include sales that were unshipped (carryover sales) at the end of the marketing year. |
| **Net Sales or Net Changes**\- The sum total resulting from new export sales, increases resulting from changes in destination, decreases resulting from changes in destination, decreases resulting from purchases from foreign sellers, and cancellations resulting from contract adjustments, buybacks, loading tolerances, changes in marketing year, or change in commodity. |
| **Total Commitment** \- The grand total of outstanding sales plus accumulated exports by country and/or commodity at any given time during the marketing year.  |

