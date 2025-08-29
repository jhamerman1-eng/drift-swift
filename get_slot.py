from solana.rpc.api import Client
solana_client = Client("https://thrumming-omniscient-moon.solana-devnet.quiknode.pro/ea7a129663c942e13ce1c9b414c3a8da9ab7d1d9/")
print(solana_client.get_slot())

