import asyncio
from datetime import datetime
import google.auth
from google.genai import Client
from google.adk.agents import Agent
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
import pgeocode
import requests

# -------------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------------
ROOT_AGENT_NAME = "root_agent"
GEMINI_MODEL = "gemini-2.5-flash"
BQ_PROJECT_ID = "ccibt-hack25ww7-751"
BQ_DATASET_ID = "real_estate_dataset"
CENSUS_API_KEY = "12652c0b73a1cacf07c4272f3f5d275f65c0bb19"
RENTCAST_API_KEY = "YOUR_RENTCAST_API_KEY"

# -------------------------------------------------------------------------
# AGENT 2: REPORT WRITER (Defined as a Tool)
# -------------------------------------------------------------------------
REPORT_INSTRUCTION = f"""
You are a Corporate Real Estate Secretary. 
Your goal is to rewrite raw data into a formal 'Interoffice Memo' format.

You must strictly follow this template:

MEMORANDUM

TO:       Business Analyst

FROM:     Real Estate Analyst Team

DATE:     {datetime.now().strftime("%B %d, %Y")}

SUBJECT:  Investment Analysis - [Insert Location]


----------------------------------------------------------------------


EXECUTIVE SUMMARY
[Write a 2-3 sentence summary of the recommendation (Invest/Avoid) and main reason why.]


MARKET FUNDAMENTALS
[Summarize Demographics and Rent data here. Use bullet points.]


RISK ASSESSMENT
[Summarize Flood and Environmental risks here.]


CONCLUSION
[Final recommendation.]


----------------------------------------------------------------------
"""
class RealEstateTools:
    """
    A helper class to handle the specific logic of calling 3rd party APIs.
    """
    
    def __init__(self):
        # Initialize the offline zip code database
        self.nomi = pgeocode.Nominatim('us')

    def get_demographics(self, zip_code: str):
        """
        Fetches Median Household Income and Population from US Census (ACS 5-Year).
        Variables: B01003_001E (Pop), B19013_001E (Median Income)
        """
        if "YOUR_" in CENSUS_API_KEY:
            return "Error: Census API Key not configured."

        year = "2021" # Uses 2021 ACS 5-Year Data
        url = f"https://api.census.gov/data/{year}/acs/acs5"
        
        params = {
            'get': 'NAME,B01003_001E,B19013_001E',
            'for': f'zip code tabulation area:{zip_code}',
            'key': CENSUS_API_KEY
        }
        
        try:
            response = requests.get(url, params=params)
            # Census returns [["NAME","B01003_001E","B19013_001E"], ["ZCTA5 10001", "23123", "92000"]]
            data = response.json()
            
            if len(data) > 1:
                return {
                    "zip_code": zip_code,
                    "population": data[1][1],
                    "median_household_income": f"${data[1][2]}"
                }
            return "Demographic data not found for this zip code."
        except Exception as e:
            return f"Failed to fetch Census data: {str(e)}"

def check_fema_flood_history(zip_code: str):
    """
    Queries FEMA's official database for historical 'Flood' disaster declarations
    in the county associated with the given zip code.
    """
    # 1. GEOCODING: Convert Zip -> County
    nomi = pgeocode.Nominatim('us')
    geo = nomi.query_postal_code(zip_code)
    
    # Check if zip exists
    if str(geo.place_name) == 'nan':
        return f"Could not find location data for zip code {zip_code}."

    state_code = geo.state_code  # e.g., 'FL'
    county_name = geo.county_name.replace(" County", "") # e.g., 'Miami-Dade'
    
    print(f"DEBUG: Looking up FEMA data for {county_name}, {state_code}...")

    # 2. FEMA API SETUP
    base_url = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
    
    # We use OData $filter syntax to query the API
    # Logic: State is X AND County is Y AND Type is 'Flood'
    query_filter = (
        f"state eq '{state_code}' and "
        f"designatedArea eq '{county_name} (County)' and "
        f"incidentType eq 'Flood'"
    )
    
    params = {
        '$filter': query_filter,
        '$select': 'disasterNumber,declarationDate,declarationTitle',
        '$orderby': 'declarationDate desc',
        '$top': 10  # Get last 10 events
    }
    
    try:
        # 3. CALL API
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        disasters = data.get('DisasterDeclarationsSummaries', [])
        
        if not disasters:
            return f"Good news: No major FEMA Flood Declarations found for {county_name}, {state_code} in the database."

        # 4. FORMAT RESULTS FOR AGENT
        # We summarize the data so the LLM can read it easily
        report = [f"Found {len(disasters)} major flood declarations for {county_name} County:"]
        
        for d in disasters:
            date_str = d['declarationDate'][:10] # Clean date format YYYY-MM-DD
            report.append(f"- {date_str}: {d['declarationTitle']} (Disaster #{d['disasterNumber']})")
            
        return "\n".join(report)

    except Exception as e:
        return f"Error connecting to FEMA API: {e}"

def generate_investment_memo(analysis_data: str) -> str:
    """
    Delegates to the ReportWriter agent to format raw analysis into a professional memo.
    Use this tool AFTER you have gathered all necessary data from BigQuery.
    
    Args:
        analysis_data: The raw data, statistics, and findings to be formatted.
    """
    # This function acts as the "Report Agent". 
    # It takes the data from the Root Agent and processes it with a specialized persona.
    try:
        client = Client()
        prompt = f"{REPORT_INSTRUCTION}\n\nRAW DATA TO FORMAT:\n{analysis_data}"
        
        response = client.models.generate_content(
            model=GEMINI_MODEL, 
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Error generating report: {str(e)}"

# --- INSTANTIATE TOOLS ---
tool_helper = RealEstateTools()

# -------------------------------------------------------------------------
# AGENT 1: ROOT COORDINATOR (Data Fetcher)
# -------------------------------------------------------------------------

# 1. Setup BigQuery Tool
tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)
creds, _ = google.auth.default()
bq_config = BigQueryCredentialsConfig(credentials=creds)
bigquery_toolset = BigQueryToolset(credentials_config=bq_config, bigquery_tool_config=tool_config)

# 2. Define Root Agent
root_agent = Agent(
    model=GEMINI_MODEL,
    name=ROOT_AGENT_NAME,
    description="Coordinator agent that fetches data and delegates reporting",
    instruction="""You are the main customer service assistant for the Property Analyzer tool.
        Your job is to interact with users, understand their requests for real estate data, and use the 'bigquery_realtor_search' tool to provide accurate and insightful information. If needed for info on zip code use census_tool.

        **Your Data Context:**
        All data is located in the Google Cloud Project ccibt-hack25ww7-751 within the BigQuery Dataset real_estate_dataset.

        **Available Tables and Their Contents:**
        *   **commercial_real_estate**: Contains details for commercial properties, including address and other relevant attributes.
        *   **nfib_losses_by_state**: Contains financial loss data by state, specifically "Open Losses" and "Closed Without Payment Losses" columns. States with high values in these columns indicate higher risk.
        *   **nfib_policy_loss_stats_by_flood_zone_policy_stats**: Provides policy counts and details related to specific flood zones, broken down by state.
        *   **realtor_daat**: This is the primary table for residential for-sale properties, typically listed by zip_code. It also contains other property details. This table can often be joined with other datasets (like nfib_losses_by_state or nfib_policy_loss_stats_by_flood_zone_policy_stats) using a common state column to provide broader insights.
        *    **safmr_2025**: This is the Small Area Fair Market Rents by Zip_code for properties of different sizes.  
        **To effectively help the user, follow these steps:**

        1.  **Greeting:** If this is the start of a conversation, warmly welcome the user to the Property Analyzer tool.
        2.  **Clarify and Interpret Request:**
            *   Listen carefully to the user's question, identifying key entities (e.g., specific states, zip codes, commercial/residential properties) and requested metrics (e.g., average price, number of policies, loss amounts, risk assessment).
            *   If the user's request is unclear, politely ask for more specific details (e.g., "Which state are you interested in?", "Are you looking for residential or commercial properties?", "What specific information about losses are you seeking?").
        3.  **Tool Usage - bigquery_toolset:**
            *   **When to use:** Use this tool when the user asks for any data that can be retrieved or analyzed from the BigQuery tables described above. This includes, but is not limited to:
                *   Property prices, beds, baths, or sizes for residential listings (realtor_daat).
                *   Commercial property details (commercial_real_estate).
                *   Financial loss data or risk assessment by state (nfib_losses_by_state).
                *   Flood zone policy statistics by state (nfib_policy_loss_stats_by_flood_zone_policy_stats).
                *   Small area fair market rents by zip code(safmr_2025).
                *   Questions that require combining information from multiple tables (e.g., "What is the average price of homes in states with high open losses?").
            *   **How to call:** The tool expects a single query parameter. This query should be a clear, concise natural language question that directly asks for the information needed from BigQuery, leveraging the knowledge of the tables and their contents.
            *   **Example Call Formats:**
                *   To find residential property details: bigquery_toolset(query='average price and median beds for residential properties in California')
                *   To assess risk: bigquery_toolset(query='list states with high open losses')
                *   To combine data: bigquery_toolset(query='what is the average price of homes in states that have more than 1000 policies in flood zone A?')
                *   To query commercial properties: bigquery_toolset(query='find commercial properties on Elm Street in New York')
                *   For specific zip codes: bigquery_toolset(query='show me residential properties listed in zip code 00680')
                *   To query safe market rents by Zip code(query='show me safmr rent for zip 12123')` 
                *   **For Comprehensive Zip Code Analysis**: When a user requests a broad overview of a specific zip code, your goal is to synthesize information from multiple tables. Construct a query for the bigquery_toolset that retrieves for-sale properties from realtor_daat, fair market rents from safmr_2025, and the associated state-level risk data from nfib_losses_by_state and nfib_policy_loss_stats_by_flood_zone_policy_stats.
                    *   **Example**: bigquery_toolset(query='For zip code 12123, show me properties for sale, the Small Area Fair Market Rents, and the state-level financial losses and flood zone statistics.')

            *   **Important:** Formulate the query for the tool as intelligently and specifically as possible, considering which tables are relevant for the user's request.
        4.  **Synthesize and Present Results:**
            *   After receiving data (or an error) from the bigquery_toolset tool, present the findings to the user in a clear, concise, and easy-to-understand natural language format.
            *   If the tool indicates an error or returns no relevant data, apologize and suggest rephrasing the question or asking for different information.
            *   Format numerical or tabular data for readability.
        5.  **Maintain Context:** Strive to remember previous turns in the conversation to provide relevant follow-up questions and more personalized assistance.
        **Rules:**
        - Always query BigQuery first. 
        - If specific zip code analysis is requested:
            - Use bigquery_toolset and get_demographics to get property and rent data
            - Use check_fema_flood_history for flood risk history if zip code is available from response.
        - Use get_demographics for Census data (population, income)
        - Always delegate to `generate_investment_memo` for the final output.
        """,
    # We pass BOTH the BQ tools and the "Report Agent" tool
    tools=[bigquery_toolset, tool_helper.get_demographics, check_fema_flood_history, generate_investment_memo],
)
