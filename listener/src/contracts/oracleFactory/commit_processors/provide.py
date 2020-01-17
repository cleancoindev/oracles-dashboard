from models import OracleRate, ProvideRate
from contracts.commit_processor import CommitProcessor
import requests
import os
from contracts.oracleFactory.oracleFactory import oracle_factory_interface
import web3
import statistics
from datetime import datetime, timedelta
from ethereum_connection import EthereumConnection
from ethereum_connection import ContractConnection

API_ENDPOINT = os.environ.get("DISCORD_WEBHOOK")
API_ENDPOINT_ALERT = os.environ.get("DISCORD_WEBHOOK_ALERT")
API_KEY = os.environ.get("WEBHOOK_KEY")
API_KEY_ALERT = os.environ.get("WEBHOOK_KEY_ALERT")

MAX_TIME_TOLERATED=os.environ.get("MAX_TIME_TOLERATED")
MAX_PERCENTAGE_OUTDATED=os.environ.get("MAX_PERCENTAGE_OUTDATED")
MAX_PERCENTAGE_ABRUPT_CHANGE=os.environ.get("MAX_PERCENTAGE_ABRUPT_CHANGE")

ABI_PATH = os.path.join(
    "/project/contracts/oracleFactory/abi",
    "MultiSourceOracle.json"
)
URL_NODE = os.environ.get("URL_NODE")

eth_conn = EthereumConnection(URL_NODE)

class Provide(CommitProcessor):
    def __init__(self):
        self.opcode = "provide_oracleFactory"

    def update_or_insert_rate(self, data):
        try:
            # update value provided by signer 
            provideRate = ProvideRate.objects.get(oracle=data.get("oracle"), signer=data.get("signer"))
            provideRate.rate = data.get("rate")
            provideRate.save()

        except Exception:
             # insert new oracle-signer value provided 
            provideRate1 = ProvideRate()
            provideRate1.oracle = data.get("oracle")
            provideRate1.signer = data.get("signer")
            provideRate1.rate = data.get("rate")

            provideRate1.save()
            pass

        oracleRates = ProvideRate.objects(oracle=data.get("oracle")).only('rate').order_by('+rate')
        rateListsorted = list(map(lambda x: int(x.rate), oracleRates))
        median_rate = int(statistics.median(rateListsorted))  

        return median_rate

    def all_provides_webhook(self, oracleRate, get_symbol, signer_name, rate_decimals, median_rate_decimals, commit):
        separation = '-----' + '\n' 
        title = 'New Rate Provided: ' + get_symbol + '/RCN' + '\n' 
        oracle = 'Oracle: ' + oracleRate.oracle + '\n'
        signer = 'Signer:' + oracleRate.signer + '\n'
        signer = 'Signer Name: ' + signer_name  + '\n' 
        raw_rate = 'Raw Rate:' + oracleRate.raw_rate + '\n'  
        rate = 'Rate:' + str("{:.10f}".format(rate_decimals)) + '\n'      
        symbol = 'Symbol: ' + get_symbol + '\n'    
        timestamp = 'Timestamp: ' + str(commit.timestamp) + '\n'  
        time_bson = 'Time Bson:' +  str(datetime.fromtimestamp(commit.timestamp)) + '\n' 
        median = 'Median Rate: ' +  str("{:.10f}".format(median_rate_decimals)) + '\n'      

        rate_provided_data = separation + title + oracle + signer + rate + raw_rate + symbol + time_bson + timestamp + median + separation      
   
        # data to be sent to api 
        payload = {'username':'Test', 
                    'content': rate_provided_data } 
        
        try:    
            # sending post request and saving response as response object 
            requests.post(url = API_ENDPOINT + API_KEY, data = payload) 
        except Exception:
            pass

    def alert_webhook_signers_outdated(self, oracleRate, get_symbol, signer_name):
        now = datetime.now()
        maxDif = int(MAX_TIME_TOLERATED) * 60
        max_peercentage_outdated = int(MAX_PERCENTAGE_OUTDATED)

        pipeline = [
        {"$match" : {  "symbol" : get_symbol }  },
        {"$sort" : {"time_bson" : 1}},
        {"$group" : {"_id" : "$signer_name", "lastRate" : { "$last": { "$floor": { "$divide": [ { "$subtract": [ now, "$time_bson" ] }, 1000] }}}}},
        {"$project" :  { "signer":"$signer",  "Last_Update" : "$lastRate"} }
        ]

        last_updates_currency = list(OracleRate.objects.aggregate(*pipeline))

        count_signers_outdated = 0
        log_signers_updates = ''
        log_provider = ''

        for signer_update in last_updates_currency:
            if signer_update["_id"] != signer_name:
                log_last_update = str(timedelta(seconds=signer_update["Last_Update"]))
                log_signer_update = 'Signer: ' + signer_update["_id"] + ' - Last Update: ' + log_last_update + ' ago  - Up to date' + '\n' 

                if signer_update["Last_Update"] > maxDif:
                    log_signer_update = 'Signer: ' + signer_update["_id"] + ' - Last Update: ' + log_last_update + ' ago  - Outdated' + '\n'  
                    count_signers_outdated += 1   

                log_signers_updates += log_signer_update
            else: 
               log_provider = 'Signer: ' + signer_update["_id"] + ' - Recently provided  - Up to date' + '\n'     
                
        percentage_outdated = 0 
        if (len(last_updates_currency) > 0): 
            percentage_outdated = count_signers_outdated * 100 / len(last_updates_currency)

        separation = '-----' + '\n' 
        max_tolarated_time = 'Max time tolerated: ' + str(MAX_TIME_TOLERATED) + ' min' + '\n'  
        alert_currency_outdated =  get_symbol + ' OUTDATED!!' + '   '
        alert_percentege_signers = str(percentage_outdated) + '% of the signers outdated!' + '\n'  + log_provider + log_signers_updates  

        alert_message = separation + alert_currency_outdated + alert_percentege_signers + max_tolarated_time + separation
        
        if (percentage_outdated >= max_peercentage_outdated): 
            payload = {'username':'Test', 
                        'content': alert_message }             
            try:
                # sending post request and saving response as response object 
                requests.post(url = API_ENDPOINT_ALERT + API_KEY_ALERT, data = payload) 
            except Exception:
                pass    
   
    def alert_webhook_median_abrupt_change(self, oracleRate, get_symbol, new_median_rate):

        max_abrupt_percentage_change = int(MAX_PERCENTAGE_ABRUPT_CHANGE)

        pipeline = [
        { "$match" :    {   "symbol" : get_symbol }  },
        {"$sort" : {"time_bson" : 1}}, 
        {"$group" : {"_id" : "$oracle", "lastRate" : { "$last": "$raw_median_rate" }}}, 
        {"$project" :  { "Last_median" : "$lastRate"} }
        ]

        last_median = list(OracleRate.objects.aggregate(*pipeline)) 

        percentage_change = 0
        last_median_rate = ''
        if (len(last_median) > 0): 
            last_median_rate = last_median[0]["Last_median"]
            if int(last_median_rate) > 0:
                percentage_change = abs(100 - (int(new_median_rate) * 100 / int(last_median_rate)))   

        separation = '-----' + '\n' 
        max_change_percentage_tolerated = 'Max change percentage tolerated: ' + str(max_abrupt_percentage_change) + ' %' + '\n'  
        alert_currency_abrupt_change =  get_symbol + ' ABRUPT CHANGE!!' + '\n' 
        alert_rates_changes = 'Last Median Rate: ' + last_median_rate + '\n' + 'New Median Rate: ' + str(new_median_rate) + '\n' 
        alert_percentage_change = 'Percentage changed: ' + str(percentage_change) + '\n' + '\n' 

        alert_message = separation + alert_currency_abrupt_change + alert_rates_changes + alert_percentage_change + max_change_percentage_tolerated + separation              

        if (percentage_change > max_abrupt_percentage_change):
            payload = {'username':'Test', 
                        'content': alert_message }             
            try:
                # sending post request and saving response as response object 
                requests.post(url = API_ENDPOINT_ALERT + API_KEY_ALERT, data = payload) 
            except Exception:
                pass    

    def process(self, commit, *args, **kwargs):
        data = commit.data

        oracleRate = OracleRate()

        oracleRate.oracle = data.get("oracle")
        oracleRate.signer = data.get("signer")
        oracleRate.raw_rate = data.get("rate")

        median_rate = self.update_or_insert_rate(data)

        contract_connection_oracle = ContractConnection(eth_conn, oracleRate.oracle, ABI_PATH)
        contract_oracle = contract_connection_oracle.contract.functions

        signer_name = contract_oracle.nameOfSigner(oracleRate.signer).call()
        decimals = contract_oracle.decimals().call()
        median_rate_decimals = int(median_rate) / (10 ** 18) / (10 ** decimals)

        get_symbol = oracle_factory_interface.get_symbol(oracleRate.oracle)
        rate_decimals = int(oracleRate.raw_rate) / (10 ** 18) / (10 ** decimals)

        # Webhook all provides
        self.all_provides_webhook(oracleRate, get_symbol, signer_name, rate_decimals, median_rate_decimals, commit)

        block_timestamp_latest =  contract_connection_oracle.w3.eth.getBlock('latest').timestamp
        block_timestamp_event = commit.timestamp

        #Webhook for alerts 
        if ((block_timestamp_latest - block_timestamp_event) < 100):   
            self.alert_webhook_signers_outdated(oracleRate, get_symbol, signer_name)
            self.alert_webhook_median_abrupt_change(oracleRate, get_symbol, median_rate)

        oracleRate.signer_name = signer_name
        oracleRate.rate = str("{:.10f}".format(rate_decimals))
        oracleRate.median_rate = str("{:.10f}".format(median_rate_decimals))
        oracleRate.raw_median_rate = str(median_rate)
        oracleRate.symbol = get_symbol
        oracleRate.timestamp = str(commit.timestamp)
        oracleRate.time_bson = datetime.fromtimestamp(commit.timestamp)
    
        commit.save()
        oracleRate.save()

        