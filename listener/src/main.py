from event_buffer import EventBuffer
from listener import Listener
from processor import Processor
from contract_manager import ContractManager
from contracts.oracleFactory.oracleFactory import Oraclefactory

all_contracts = [Oraclefactory]

contract_manager = ContractManager(all_contracts)


def run():
    buffer = EventBuffer()
    processor = Processor(buffer, contract_manager)
    listener = Listener(buffer, contract_manager)
    listener.run()


if __name__ == '__main__':
    run()
