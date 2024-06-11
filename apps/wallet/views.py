from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from bitcoinutils.transactions import Transaction , TxInput , TxOutput, TxWitnessInput
from bitcoinutils.keys import P2pkhAddress, P2wpkhAddress, PrivateKey
from bitcoinutils.script import Script
from hdwallet.symbols import BTCTEST as SYMBOL #  BTC as SYMBOL
from hdwallet import BIP141HDWallet
from .models import Wallet, UTXO
from .serializers import GetWalletSerializer
import requests
import os

# ----------------------------------------- GET -------------------------------------------------
class GetWallet(APIView):
  permission_classes = (permissions.IsAuthenticated, )
  def get(self, request, format=None):
    user = request.user
    sales = get_object_or_404(Wallet , user=user)
    serializer = GetWalletSerializer(sales)
    return Response(serializer.data, status=status.HTTP_200_OK)
# ----------------------------------------- POST ------------------------------------------------
class Withdraw(APIView):
  permission_classes = (permissions.IsAuthenticated, )

  def get_utxo_data(self, address: str):
    """
    Get the list of unspent transaction outputs associated with the address/scripthash
    ---------------
    ```
    [
      {
        txid: "12f96289f8f9cd51ccfe390879a46d7eeb0435d9e0af9297776e6bdf249414ff",
        vout: 0,
        status: {
          confirmed: true,
          block_height: 698642,
          block_hash: "00000000000000000007839f42e0e86fd53c797b64b7135fcad385158c9cafb8",
          block_time: 1630561459
        },
        value: 644951084
      },
      ...
    ]
    ```
    """
    try:
      response = requests.get(url=f'https://mempool.space/testnet/api/address/{address}/utxo')
      data = response.json()
      if data and data[0]["status"]["confirmed"]:
        return str(data[0]["txid"]), int(data[0]["vout"]), int(data[0]["value"])
    except Exception as e:
      return str(e)

  def generate_btc_address(self, path):
    MNEMONIC = os.getenv('MNEMONIC')
    PASSPHRASE = os.getenv('PASSWORD')
    numbers = [char for char in str(path) if char.isdigit()]
    numbers_str = ''.join(numbers)
    derivation_path = f"m/{numbers_str[0:2]}/{numbers_str[2:4]}/{numbers_str[4:6]}'/{numbers_str[6:9]}'/{numbers_str[9:12]}'/{numbers_str[12:14]}/{numbers_str[14:16]}"
    hdwallet = BIP141HDWallet(symbol=SYMBOL, path=derivation_path)
    hdwallet.from_mnemonic(mnemonic=MNEMONIC, language='english', passphrase=PASSPHRASE)
    return hdwallet.hash(), hdwallet.compressed(), hdwallet.wif()

  def get_less_fees(self, amount_sat: int) -> int:
    try:
      recommended_fees = requests.get(url="https://mempool.space/testnet/api/v1/fees/recommended")
      fee_data = recommended_fees.json()
      # Fórmula de tamaño de transacción: (witness)
			# (Numero de inputs × 68) + (Numero de outputs × 31) + 10
      # Tarifa = Tamaño de la transaccion × Tarifa por byte
      # les_fee_sat = 140 * fee_data["fastestFee"] MAINET
      les_fee_sat = 1 # TESTNET
      print(f'Fee SAT: {les_fee_sat}')
      print(f'Ammount SAT: {amount_sat}')
      amount_less_fee = amount_sat - les_fee_sat
      return amount_less_fee
    except Exception as e:
      return str(e)

  def input_p2wpkh_to_p2pkh(self, pub_to_hash160: str, pub_to_hex: str, tx_id: str, vout: int, amount: int, address_to: str, wif: str):
    try:        
      txin = TxInput(tx_id, vout)
      to_addr = P2pkhAddress(address_to)
      amount_to_send = self.get_less_fees(amount)
      tx_out = TxOutput(amount_to_send, to_addr.to_script_pub_key())
      tx = Transaction([txin], [tx_out], has_segwit=True)
      print("\nRaw transaction:\n" + tx.serialize())
      print("\ntxin:\n", txin)
      print("\ntoAddr:\n", to_addr.to_string())
      print("\ntxOut:\n", tx_out)
      script_code = Script(['OP_DUP', 'OP_HASH160', pub_to_hash160, 'OP_EQUALVERIFY', 'OP_CHECKSIG'])
      priv = PrivateKey(wif)
      sig = priv.sign_segwit_input(tx, 0, script_code, amount)
      tx.witnesses.append(TxWitnessInput([sig, pub_to_hex]))
      print("\nRaw signed transaction:\n" + tx.serialize())
      print("\nTxId:", tx.get_txid())
      envio = requests.post(url='https://mempool.space/testnet/api/tx', data=tx.serialize())
      print(envio.status_code)
      print(envio.text)
      return True
    except Exception as e:
      return str(e)

  def input_p2wpkh_to_p2wpkh(self, pub_to_hash160: str, pub_to_hex: str, tx_id: str, vout: int, amount: int, address_to: str, wif: str):
    try:
      txin = TxInput(tx_id, vout)
      to_addr = P2wpkhAddress(address_to)
      amount_to_send = self.get_less_fees(amount)
      tx_out = TxOutput(amount_to_send, to_addr.to_script_pub_key())
      tx = Transaction([txin], [tx_out], has_segwit=True)
      print("\nRaw transaction:\n" + tx.serialize())
      print("\ntxin:\n", txin)
      print("\ntoAddr:\n", to_addr.to_string())
      print("\ntxOut:\n", tx_out)
      script_code = Script(['OP_DUP', 'OP_HASH160', pub_to_hash160, 'OP_EQUALVERIFY', 'OP_CHECKSIG'])
      priv = PrivateKey(wif)
      sig = priv.sign_segwit_input(tx, 0, script_code, amount)
      tx.witnesses.append(TxWitnessInput([sig, pub_to_hex]))
      print("\nRaw signed transaction:\n" + tx.serialize())
      print("\nTxId:", tx.get_txid())
      envio = requests.post(url='https://mempool.space/testnet/api/tx', data=tx.serialize())
      print(envio.status_code)
      print(envio.text)
      return True
    except Exception as e:
      return str(e)

  def verify_address(self, address_to):
    try:
      validation = requests.get(url=f"https://mempool.space/testnet/api/v1/validate-address/{address_to}")
      data_info = validation.json()
      if data_info["isvalid"]:
        if data_info['isscript'] == False and data_info['iswitness'] == False:
          address_type = 'legacy'
        elif data_info['iswitness']:
          address_type = 'witness'
        else:
          return False, None
        return True, address_type
      else:
        return False, None
    except Exception as e:
      return False, str(e)

  def post(self, request, format=None):
    user = request.user
    data = request.data
    address_to = data.get('addressTo')
    wallet = get_object_or_404(Wallet , user=user)
    is_valid, address_type = self.verify_address(address_to)
    if is_valid and wallet.amountInCrypto != 0.0:
      active_utxos = UTXO.objects.filter(user=user, status='active')
      addresses = [utxo.address for utxo in active_utxos]
      for address in addresses:
        utxo = get_object_or_404(UTXO, address=address)
        pub_to_hash160, pub_to_hex, wif = self.generate_btc_address(path=utxo.slug)
        txid, vout, amount_in_sat = self.get_utxo_data(address)
        if address_type == 'legacy':
          send = self.input_p2wpkh_to_p2pkh(pub_to_hash160=pub_to_hash160,
																		pub_to_hex=pub_to_hex, 
																		tx_id=txid, 
																		vout=vout, 
																		amount=amount_in_sat, 
																		address_to=address_to,
																		wif=wif
																		)
        elif address_type == 'witness':
          send = self.input_p2wpkh_to_p2wpkh(pub_to_hash160=pub_to_hash160,
                                    pub_to_hex=pub_to_hex, 
                                    tx_id=txid, 
                                    vout=vout, 
                                    amount=amount_in_sat, 
                                    address_to=address_to,
                                    wif=wif
                                    )
      if send:
        wallet.amountInCrypto = 0.0
        wallet.save()
        return Response({'Success': "sended"}, status=status.HTTP_200_OK)
    else:
      return Response({'error': address_type}, status=status.HTTP_406_NOT_ACCEPTABLE)