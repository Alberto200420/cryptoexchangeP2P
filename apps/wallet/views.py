from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction
from django.shortcuts import get_object_or_404
from bitcoinutils.transactions import Transaction , TxInput , TxOutput, TxWitnessInput
from bitcoinutils.keys import P2pkhAddress, P2wpkhAddress, PrivateKey
from bitcoinutils.script import Script
from bitcoinutils.utils import to_satoshis
from hdwallet.symbols import BTCTEST as SYMBOL #  BTC as SYMBOL
from hdwallet import BIP141HDWallet
from .models import Wallet, UTXO
from .serializers import *
import requests
import os
import logging
logger = logging.getLogger(__name__)

# ----------------------------------------- GET -------------------------------------------------
class GetWallet(APIView):
  permission_classes = (permissions.IsAuthenticated, )
  def get(self, request, format=None):
    user = request.user
    sales = get_object_or_404(Wallet , user=user)
    serializer = GetWalletSerializer(sales)
    return Response(serializer.data, status=status.HTTP_200_OK)

# class GetUTXO(APIView):
#   permission_classes = (permissions.IsAuthenticated, )
#   def get(self, request, format=None):
#     user = request.user
#     sales = get_object_or_404(UTXO , user=user)
#     serializer = GetUTXOtSerializer(sales)
#     return Response(serializer.data, status=status.HTTP_200_OK)
# ----------------------------------------- POST ------------------------------------------------
class Withdraw(APIView):
  permission_classes = (permissions.IsAuthenticated, )

  def checkTxPrevInputType(self, tx: str, address: str) -> bool:
    """
    Retorna si la tx recibida fue con segwit
    """
    try:
      txData = requests.get(url=f'https://mempool.space/testnet/api/tx/{tx}')
      dato = txData.json()
      # Recorremos la lista de salidas para encontrar la dirección especificada
      for output in dato['vout']:
        if output['scriptpubkey_address'] == address:
          typeOf = output['scriptpubkey_type']
          if typeOf == 'v0_p2wpkh':
            return True
          else:
            return False
      # Si no se encuentra la dirección en las salidas, retornamos False
      return False
    except Exception as e:
      logger.error(f"Error occurred checkTxPrevInputType(): {e}")
      return False

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
      logger.error(f"Error occurred get_utxo_data(): {e}")
      return None

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
    """
    TAMAÑO DE TRANSACCION
    ----------------------------
    Legacy Address (P2PKH): (Numero de inputs × 148) + (Numero de outputs × 34) + 10
    Pay-to-Script-Hash (P2SH): (Numero de inputs × 92) + (Numero de outputs × 34) + 10
    Pay-to-Witness-Public-Key-Hash (P2WPKH): (Numero de inputs × 68) + (Numero de outputs × 31) + 10
    Pay-to-Witness-Script-Hash (P2WSH): (Numero de inputs × 68) + (Numero de outputs × 43) + 10

    >>> Tarifa = Tamaño de la transaccion × Tarifa por byte

    >>> (1 INPUT = 68) + (2 OUTPUS = 62) + 10 = 140
    """
    try:
      recommended_fees = requests.get(url="https://mempool.space/testnet/api/v1/fees/recommended")
      fee_data = recommended_fees.json()
      # les_fee_sat = 140 * fee_data["minimumFee"]
      les_fee_sat = 140 * 35
      print(f'Fee SAT: {les_fee_sat}')
      print(f'Ammount SAT: {amount_sat}')
      amount_less_fee = amount_sat - les_fee_sat
      return amount_less_fee
    except Exception as e:
      logger.error(f"Error occurred get_less_fees(): {e}")
      return None

  def commission(self):
    try:
      response = requests.get(url=f'https://mempool.space/api/v1/prices')
      data = response.json()
      price_per_btc_usd = data["USD"]     # Obtener el precio de 1 Bitcoin en USD
      btc_per_usd = 1 / price_per_btc_usd # Calcular cuánto Bitcoin se obtiene por 1 dólar
      commissionSatoshis = to_satoshis(btc_per_usd)
      print(f'Precio por 1 Bitcoin en USD: ${price_per_btc_usd}')
      print(f'Cantidad de Satoshis por 1 USD fromateado: {to_satoshis(btc_per_usd)} SAT')
      envVar = os.getenv('ADDRESS_COMMISSION')
      if envVar is None:
        logger.error(f"Error occurred commission(): {e}")
        raise ValueError("Environment variable 'ADDRESS_COMMISSION' is not set")
      commission_addr = P2wpkhAddress(envVar)
      print(f'commissionSatoshis: {commissionSatoshis}')
      return commissionSatoshis, commission_addr
    except Exception as e:
      logger.error(f"Error occurred commission(): {e}")
      return None

  def input_p2wpkh_to_p2pkh(self, pub_to_hash160: str, pub_to_hex: str, tx_id: str, vout: int, amount: int, address_to: str, wif: str):
    try:        
      txin = TxInput(tx_id, vout)
      to_addr = P2pkhAddress(address_to)
      amount_les_fees = self.get_less_fees(amount)
      commissionSatoshis, commission_addr = self.commission()
      amount_to_send = amount_les_fees - commissionSatoshis
      tx_out = TxOutput(amount_to_send, to_addr.to_script_pub_key())
      commission_out = TxOutput(commissionSatoshis, commission_addr.to_script_pub_key())
      tx = Transaction(inputs=[txin], outputs=[tx_out, commission_out], has_segwit=True)
      print("\nRaw transaction:\n" + tx.serialize())
      print("\ntxin:\n", txin)
      print("\ntoAddr:\n", to_addr.to_string())
      print("\ntxOut:\n", tx_out)
      print("\ncommission_out:\n", commission_out)
      print("\ntx:\n", tx)
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
      logger.error(f"Error occurred input_p2wpkh_to_p2pkh(): {e}")
      return False

  def input_p2wpkh_to_p2wpkh(self, pub_to_hash160: str, pub_to_hex: str, tx_id: str, vout: int, amount: int, address_to: str, wif: str):
    try:
      txin = TxInput(tx_id, vout)
      to_addr = P2wpkhAddress(address_to)
      amount_les_fees = self.get_less_fees(amount)
      commissionSatoshis, commission_addr = self.commission()
      amount_to_send = amount_les_fees - commissionSatoshis
      tx_out = TxOutput(amount_to_send, to_addr.to_script_pub_key())
      commission_out = TxOutput(commissionSatoshis, commission_addr.to_script_pub_key())
      tx = Transaction(inputs=[txin], outputs=[tx_out, commission_out], has_segwit=True)
      print("\nRaw transaction:\n" + tx.serialize())
      print("\ntxin:\n", txin)
      print("\ntoAddr:\n", to_addr.to_string())
      print("\ntxOut:\n", tx_out)
      print("\ncommission_out:\n", commission_out)
      print("\ntx:\n", tx)
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
      logger.error(f"Error occurred input_p2wpkh_to_p2wpkh(): {e}")
      return False

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
      logger.error(f"Error occurred verify_address(): {e}")
      return False, None

  with transaction.atomic():
    def post(self, request, format=None):
      user = request.user
      data = request.data
      address_to = data.get('addressTo')
      wallet = get_object_or_404(Wallet, user=user)
      is_valid, address_type = self.verify_address(address_to)
      if is_valid and wallet.amountInCrypto != 0.0:
        active_utxos = UTXO.objects.filter(user=user, status='active')
        addresses = [utxo.address for utxo in active_utxos]
        send = False  # Initialize send to False to track if any UTXO was successfully sent
        for address in addresses:
          utxo = get_object_or_404(UTXO, address=address)
          pub_to_hash160, pub_to_hex, wif = self.generate_btc_address(path=utxo.slug)
          txid, vout, amount_in_sat = self.get_utxo_data(address)
          isP2wpkh = self.checkTxPrevInputType(tx=txid, address=address)
          if address_type == 'legacy' and isP2wpkh:
            send = self.input_p2wpkh_to_p2pkh(pub_to_hash160=pub_to_hash160,
                                      pub_to_hex=pub_to_hex, 
                                      tx_id=txid, 
                                      vout=vout, 
                                      amount=amount_in_sat, 
                                      address_to=address_to,
                                      wif=wif
                                      )
          if address_type == 'witness' and isP2wpkh:
            send = self.input_p2wpkh_to_p2wpkh(pub_to_hash160=pub_to_hash160,
                                      pub_to_hex=pub_to_hex, 
                                      tx_id=txid, 
                                      vout=vout, 
                                      amount=amount_in_sat, 
                                      address_to=address_to,
                                      wif=wif
                                      )
          if send:
            utxo.status = 'used'
            utxo.save()

        if send:
          wallet.amountInCrypto = 0.0
          wallet.save()
          return Response({'Success': "sended"}, status=status.HTTP_200_OK)
        else:
          return Response({'error': 'No UTXO was sent successfully'}, status=status.HTTP_400_BAD_REQUEST)
      else:
        return Response({'error': address_type}, status=status.HTTP_406_NOT_ACCEPTABLE)