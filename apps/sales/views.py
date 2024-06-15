from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from hdwallet import BIP141HDWallet
from hdwallet.symbols import BTCTEST as SYMBOL #  BTC as SYMBOL
from .models import Sale
from .serializers import *
from apps.user_profile.models import Profile
from apps.wallet.models import Wallet, UTXO
import os
import time
import requests
FROM_EMAIL = settings.DEFAULT_FROM_EMAIL
DOMAIN = settings.DOMAIN
ADMIN = os.getenv('ADMIN')
import logging
logger = logging.getLogger(__name__)

# ----------------------------------------- POST -------------------------------------------------
class CreateSalePostView(APIView):
  """
  Primero obtiene los parametros dados en el request -> bankEntity, reference, (accountNumber <- (opcional))
  luego llama a:
  ```
  create_sale_and_address()
  ```
  
  despues los serializa, una vez serializados los guarda en la base de datos y obtiene el slug}
  ```
  def create_sale_and_address(self, serializer, request):
    sale = serializer.save(user=request.user)
    slug = sale.slug
    address = self.generate_btc_address(slug) # Generar una dirección de Bitcoin basada en un derivation path
  ```
  Generar una dirección de Bitcoin basada en un derivation path

  1 - Recupera el MNEMONIC y PASSPHRASE desde las variables de entorno
  2 - Extrae los dígitos del path proporcionado y los usa para construir un derivation_path

  3 - Utiliza BIP141HDWallet para generar una dirección de Bitcoin a partir del mnemonic y el derivation path

  4 - Devuelve la dirección generada

  Despues de obtener el addres en una bariable
  ```
  address = self.generate_btc_address(slug)
  ```
  Genera una dirección de Bitcoin basada en el slug de la venta.
  Asigna la dirección generada a la venta y guarda los cambios.
  Actualiza el perfil del usuario incrementando el número de publicaciones creadas (postsCreated).
  Devuelve la dirección generada.

  Si se completa con éxito, devuelve una respuesta con la dirección generada y un estado HTTP 201.
  Si ocurre una excepción: Devuelve una respuesta con el error y un estado HTTP 500.
  Si los datos no son válidos: Devuelve los errores del serializer y un estado HTTP 400.

  """

  permission_classes = (permissions.IsAuthenticated, )
    
  def generate_btc_address(self, path):
    MNEMONIC = os.getenv('MNEMONIC')
    PASSPHRASE = os.getenv('PASSWORD')
    numeros = [char for char in str(path) if char.isdigit()]
    numeros_str = ''.join(numeros)
    derivation_path = f"m/{numeros_str[0:2]}/{numeros_str[2:4]}/{numeros_str[4:6]}'/{numeros_str[6:9]}'/{numeros_str[9:12]}'/{numeros_str[12:14]}/{numeros_str[14:16]}"
    hdwallet = BIP141HDWallet(symbol=SYMBOL, path=derivation_path)
    hdwallet.from_mnemonic(mnemonic=MNEMONIC, language='english', passphrase=PASSPHRASE)
    return hdwallet.address()
    
  def create_sale_and_address(self, serializer, request):
    sale = serializer.save(user=request.user)
    slug = sale.slug
    address = self.generate_btc_address(slug)
    sale.address = address
    sale.save()
    profile = get_object_or_404(Profile, user=request.user)
    profile.postsCreated += 1
    profile.save()
    return address
    
  def post(self, request, format=None):
    serializer = SaleCreateSerializer(data=request.data)
    if serializer.is_valid():
      try:
        address = self.create_sale_and_address(serializer, request)
        return Response({'address': address}, status=status.HTTP_201_CREATED)
      except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MakeComment(APIView):
  """
  API endpoint that allows users to post a comment on a sale item.
  --------------
  Only authenticated users can access this endpoint.

  Handle POST request to create a comment for a specific sale post identified by its slug.
        
  Expects a JSON payload with 'sale_post' (slug of the sale post) and comment details.
        
  Preconditions:
  - The sale post must exist and be identified by the provided slug.
  - The requesting user must be the buyer of the sale post.
        
  Process:
  - Retrieve the slug from the request data.
  - Fetch the Sale instance using the provided slug.
  - Update the request data with the Sale instance's primary key (pk) instead of the slug.
  - Pass the updated data to the comment serializer for validation.
  - If the serializer is valid and the user is the buyer, save the comment.
        
  Returns:
  - 201 Created: If the comment is successfully saved.
  - 400 Bad Request: If required data is missing or the serializer validation fails.
  - 404 Not Found: If the sale post identified by the slug does not exist.
  """

  permission_classes = (permissions.IsAuthenticated,)
  def post(self, request, format=None):
    # Obtener el pk del objeto Sale basado en el slug proporcionado en la solicitud
    slug = request.data.get("sale_post")
    sale = get_object_or_404(Sale, slug=slug)
    # Actualizar el diccionario de datos con el pk en lugar del slug
    request.data["sale_post"] = sale.pk
    # Pasar los datos actualizados al serializador
    serializer = CreateCommentSerializer(data=request.data)
    if serializer.is_valid() and sale.buyer == request.user:
      # Guardar el comentario
      serializer.save(user=request.user)
      return Response({"success": "Comment saved successfully"}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# ----------------------------------------- PUT -------------------------------------------------
class Buy(APIView):
  """
  API endpoint that allows users to buy a sale item by changing its status to 'taked_offer'.
  --------------
  Only authenticated users can access this endpoint.

  Handle PUT request to change the status of a Sale to 'taked_offer' and notify the owner.
        
  Expects a JSON payload with 'slug' and 'voucher' fields.
        
  Preconditions:
  - Sale instance must have a status of 'looking'.
  - Requesting user must not be the owner of the Sale instance.
        
  Process:
  - Validate the presence of 'slug' and 'voucher'.
  - Fetch the Sale instance using the provided 'slug'.
  - Check the status and ownership conditions.
  - Change status to 'taked_offer', set the buyer, and update the 'buyed_at' timestamp.
  - Use a serializer to validate and save the voucher.
  - Send an email notification to the sale owner.
        
  Returns:
  - 200 OK: If the sale status was successfully changed and the data saved.
  - 400 Bad Request: If required data is missing or the serializer validation fails.
  - 401 Unauthorized: If the sale has already been accepted by another user.
  """

  permission_classes = (permissions.IsAuthenticated,)

  def send_email(self, recipient_email, slug):
    """
    Sends an email notification to the sale owner when their offer has been accepted.
        
    Parameters:
    - recipient_email: Email of the sale owner.
    - slug: Unique identifier of the sale.
    """
    html_content = render_to_string('sale_notify.html', {
      'username': recipient_email,
      'DOMAIN': F"{DOMAIN}/trade/{slug}/confirm",
    })
    send_mail(
      subject='SOMEONE HAS ACCEPTED YOUR OFFER',
      message=f'Hi {recipient_email}, !CONGRATULATIONS!, someone has accepted your sale, visit this url {DOMAIN}/trade/{slug}/confirm to communicate with the user and close the sale.',
      from_email=FROM_EMAIL,
      recipient_list=[recipient_email],
      html_message=html_content
    )

  def put(self, request, format=None):
    data = request.data
    slug = data.get('slug')
    voucher = request.FILES.get('voucher')
    bitcoin_value = data.get('bitcoin_value')

    if not slug or not voucher:
      logger.error("No slug or voucher")
      return Response({'error': 'Slug and voucher are required'}, status=status.HTTP_400_BAD_REQUEST)

    sale = get_object_or_404(Sale, slug=slug)

    if sale.status == 'looking' and sale.user != request.user:
      sale.status = 'taked_offer'
      sale.bitcoin_value = bitcoin_value
      sale.buyer = request.user
      sale.buyed_at = timezone.now()

      # Use the serializer to validate and save the images
      serializer = BuySerializer(instance=sale, data={'slug': slug, 'voucher': voucher, 'bitcoin_value': bitcoin_value}, partial=True)
      if serializer.is_valid():
        serializer.save()
        self.send_email(sale.user.email, slug)
        return Response({'success': 'data saved successfully', 'status': sale.status}, status=status.HTTP_200_OK)
      else:
        logger.error(f"Serialization invalid: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif sale.status != 'looking':
      return Response({'error': 'Already accepted trade'}, status=status.HTTP_401_UNAUTHORIZED)
    logger.error("Request is invalid")
    return Response({'error': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)

class ChangeToLooking(APIView):
  """
  API endpoint that allows changing the status of a Sale instance to 'looking'.
  -------
  Only authenticated users can access this endpoint.

  Handle PUT request to change the status of a Sale to 'looking'.
        
  Expects a JSON payload with a 'slug' field to identify the Sale instance.
        
  Preconditions:
  - Sale instance must have a status of 'active'.
  - Requesting user must not be the owner of the Sale instance.
        
  Returns:
  - 200 OK: If the status was successfully changed.
  - 304 Not Modified: If the preconditions are not met.
  """
  
  permission_classes = (permissions.IsAuthenticated,)

  def put(self, request, format=None):
    data = self.request.data
    slug = data['slug']
    sale = get_object_or_404(Sale, slug=slug)
    if sale.status == 'active' and sale.user != request.user:
      sale.status = 'looking'
      sale.save()
      return Response({'success': 'data saved successfully', 'status': sale.status}, status=status.HTTP_200_OK)
    
    return Response({'error'}, status=status.HTTP_304_NOT_MODIFIED)

class ChangeToAtiveLoop(APIView):
  """
  Handle PUT request to periodically check and change the status of a Sale to 'active'.
  -----------------
  Expects a JSON payload with a 'slug' field to identify the Sale instance.
        
  Preconditions:
  - Sale instance must have a status of 'looking'.
  - Requesting user must not be the owner of the Sale instance.
        
  Process:
  - Check the status of the Sale instance every 3:20 minutes, up to 3 times.
  - If the status is 'taked_offer', do nothing and return a response indicating the status.
  - If after 3 attempts the status is not 'taked_offer', change it to 'active'.
        
  Returns:
  - 200 OK: If the status was successfully changed or if the status was 'taked_offer'.
  - 304 Not Modified: If the preconditions are not met.
  """
  
  permission_classes = (permissions.IsAuthenticated,)

  def put(self, request, format=None):
    data = self.request.data
    slug = data['slug']
    sale = get_object_or_404(Sale, slug=slug)
    if sale.status == 'looking' and sale.user != request.user:
      attempts = 0
      while attempts < 3:
        print(f'INTENTTO {attempts}')
        sale.refresh_from_db()
        if sale.status in ['taked_offer', 'bought']:
          return Response({'status trade': sale.status}, status=status.HTTP_200_OK)
        elif sale.status == 'active':
          return Response({'status trade': sale.status}, status=status.HTTP_200_OK)
        time.sleep(200)  # Sleep for 3:20 minutes (200 seconds)
        attempts += 1
            
      # After 3 attempts, if the status is still not 'taked_offer', set it to 'active'
      sale.refresh_from_db()
      if sale.status not in ['taked_offer', 'bought']:
        sale.status = 'active'
        sale.save()
        return Response({'success': 'Status changed to active', 'sale_status': sale.status}, status=status.HTTP_200_OK)
        
    return Response({'error': 'Preconditions not met'}, status=status.HTTP_304_NOT_MODIFIED)

class ActiveSaleLoop(APIView):
  """
  Verifica el estado de una transacción y actualizar el estado de la venta
  --------
  1 - Extrae la dirección de la solicitud mediante el request

  2 - Obtiene la venta (Sale) asociada a la dirección usando get_object_or_404

  3 - Verifica si el estado de la venta es 'pending' y si el usuario autenticado es el propietario de la venta

  Si es cierto:
    Llama a getUTXOinfo para obtener la información de UTXO

    Intenta hasta 3 veces (o hasta que se confirme la transacción):

    Si la transacción está confirmada devuelve el txid, vout, value y 
    Usa send_mail para enviar el correo con el asunto "TRANSACTION RECEIVED" al 
    correo del destinatario (recipient_email), notificando que la transacción 
    a la dirección (address) fue recibida y si no devuelve None

  ```
    self.send_transaction_received_email(request.user.email, address)
    sale.status = 'active'
    sale.save()
    return Response({'status': sale.status}, status=status.HTTP_200_OK)
  else:
    return Response({'error': 'UTXO info not found or transaction not confirmed'}, status=status.HTTP_200_OK)
  ```

  """

  permission_classes = (permissions.IsAuthenticated,)
  
  def getUTXOinfo(self, address: str):
    failedAttempts = 0
    while failedAttempts < 3:
      try:
        getUTXO = requests.get(url=f'https://mempool.space/testnet/api/address/{address}/utxo')
        dataInfo = getUTXO.json()
        if dataInfo and dataInfo[0]["status"]["confirmed"]:
          return str(dataInfo[0]["txid"]), int(dataInfo[0]["vout"]), int(dataInfo[0]["value"])
        else:
          failedAttempts += 1
      except Exception as e:
        logger.error(f"Error getting UTXO info: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR), None
      # Esperar 10 minutos antes de realizar la próxima solicitud
      time.sleep(600)  # 600 segundos = 10 minutos
    return None

  def send_transaction_received_email(self, recipient_email, address, slug):
    html_content = render_to_string('active_loop.html', {
      'username': recipient_email,
      'address': address,
      'shareLink': F"{DOMAIN}/trade/{slug}/buy",
      'viewLink': F"{DOMAIN}/dashboard/posts"
    })
    send_mail(
      subject='TRANSACTION RECEIVED',
      message=f'Hi {recipient_email}, this message is only to notify you that your transaction to the address {address} was received successfully. Share your post with this link {DOMAIN}/trade/{slug}/buy" or view your post at this link {DOMAIN}/dashboard/posts".',
      from_email=FROM_EMAIL,
      recipient_list=[recipient_email],
      html_message=html_content
    )

  def put(self, request, format=None):
    data = self.request.data
    address = data['address']
    sale = get_object_or_404(Sale, address=address)
    if sale.status == 'pending' and sale.user == request.user:
      try:
        utxo_info = self.getUTXOinfo(address)
        if utxo_info:
          txid, vout, value = utxo_info
          print(txid, vout, value)
          self.send_transaction_received_email(request.user.email, address, sale.slug)
          sale.status = 'active'
          sale.save()
          return Response({'status': sale.status}, status=status.HTTP_200_OK)
        else:
          logger.warning(f"UTXO info not found or transaction not confirmed for address: {address}")
          return Response({'error': 'UTXO info not found or transaction not confirmed'}, status=status.HTTP_200_OK)
      except Exception as e:
        logger.error(f"Error during sale activation: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
      return Response({'error': 'Sale status is not pending'}, status=status.HTTP_406_NOT_ACCEPTABLE)

class ConfirmBuy(APIView):

  """
  API endpoint that confirms a purchase by updating the sale status and related user profiles.
  ---------------
  Only authenticated users can access this endpoint.
  ```
  def getUTXO_value(self, address: str): # <- Fetches the UTXO value of a given Bitcoin address from an external API.
  ```
  Returns:
  - UTXO value in satoshis if the transaction is confirmed.

  Handle PUT request to confirm a purchase.

  Expects a JSON payload with 'slug' field.

  Preconditions:
  - Sale instance must have a status of 'taked_offer'.
  - The requesting user must be the seller.

  Process:
  - Fetch the Sale instance using the provided 'slug'.
  - Verify the status and ownership conditions.
  - Retrieve the UTXO value of the sale's address.
  - Update the sale status to 'bought'.
  - Update user profiles and buyer's wallet.
  - Send a confirmation email to the buyer.

  Returns:
  - 200 OK: If the purchase was successfully confirmed.
  - 401 Unauthorized: If the sale status is not 'taked_offer' or the user is not the seller.
  - 500 Internal Server Error: If there was an error processing the request.
  """
  permission_classes = (permissions.IsAuthenticated, )

  def send_email(self, recipient_email):
    """
    Sends a confirmation email to the buyer after the purchase is completed.
    --------
    Parameters:
    - recipient_email: Email address of the recipient.
    """
    html_content = render_to_string('sale_conpleted.html', {
      'username': recipient_email
    })
    send_mail(
      subject='Purchase completed',
      message=f'Hi {recipient_email}, Your purchase has been completed, you can now see your balance reflected in your account, remember to send your cryptocurrencies as soon as possible to a wallet that belongs to you. Thanks for choosing us Crypto exchange team',
      from_email=FROM_EMAIL,
      recipient_list=[recipient_email],
      html_message=html_content
    )

  def getUTXO_value(self, address: str):
    """
    Fetches the UTXO value of a given Bitcoin address from an external API.
    ---------
    Parameters:
    - address: Bitcoin address to fetch the UTXO value for.

    Returns:
    - UTXO value in satoshis if the transaction is confirmed.
    """
    try:
      getUTXO = requests.get(url=f'https://mempool.space/testnet/api/address/{address}/utxo')
      dataInfo = getUTXO.json()
      if dataInfo and dataInfo[0]["status"]["confirmed"]:
        return int(dataInfo[0]["value"])
      else:
        Response({'error': 'Transaction not received'}, status=status.HTTP_406_NOT_ACCEPTABLE)
    except Exception as e:
      return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

  def put(self, request, format=None):
    data = request.data
    slug = data.get('slug')
    sale = get_object_or_404(Sale, slug=slug)

    if sale.status != 'taked_offer' or sale.user != request.user:
      return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    seller_profile = get_object_or_404(Profile, user=request.user)
    buyer_profile = get_object_or_404(Profile, user=sale.buyer)
    buyer_wallet = get_object_or_404(Wallet, user=sale.buyer)

    try:
      ammountSATOSHIS = self.getUTXO_value(address=sale.address)
      if isinstance(ammountSATOSHIS, Response):
        return ammountSATOSHIS  # Return error response if UTXO retrieval failed
      
      # Utilizamos transaction.atomic() para asegurarnos de que todas las operaciones de base de datos 
      # dentro del bloque se realicen de manera atómica. Si alguna falla, ninguna de las operaciones se 
      # guardará en la base de datos.
      with transaction.atomic():
        UTXO.objects.create(user=sale.buyer, slug=sale, address=sale.address, wallet=buyer_wallet)
        sale.status = 'bought'
        sale.save()

        seller_profile.successful_exchanges += 1
        buyer_profile.successful_exchanges += 1
        seller_profile.number_of_sales += 1
        buyer_profile.number_of_purchase += 1
        inBTC = 0.00000001 * ammountSATOSHIS
        buyer_wallet.amountInCrypto += inBTC

        seller_profile.save()
        buyer_profile.save()
        buyer_wallet.save()
        self.send_email(sale.buyer.email)

      return Response({"Confirmed exchange"}, status=status.HTTP_200_OK)

    except Exception as e:
      logger.error(f"Error during sale confirmation: {e}")
      return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReportPost(APIView):
  """
  API endpoint that allows users to report a sale post and notify the relevant parties.
  ----------------------
  Only authenticated users can access this endpoint.

  Handle PUT request to report a sale post.
        
  Expects a JSON payload with 'slug' and 'message' fields.
        
  Preconditions:
  - Sale instance must have a status of 'taked_offer' or 'bought'.
  - Requesting user must be the buyer or seller of the sale.
        
  Process:
  - Fetch the Sale instance using the provided 'slug'.
  - Check the status and ownership conditions.
  - Update the profile of the reported user by incrementing their report count.
  - Change the status of the sale to 'reported'.
  - Send notification emails to the admin and the reporting user.
        
  Returns:
  - 200 OK: If the report was successfully processed.
  - 400 Bad Request: If required data is missing.
  - 401 Unauthorized: If the requesting user is not the buyer or seller of the sale.
  - 403 Forbidden: If the sale status is not 'taked_offer' or 'bought'.
  """

  permission_classes = (permissions.IsAuthenticated,)

  def report_email(self, reportingUser, userReported, url, reportingMessage):
    """
    Sends an email to the admin with details of the report.
    ---------    
    Parameters:
    - reportingUser: Email of the user who is reporting.
    - userReported: Email of the user being reported.
    - url: URL slug of the reported sale.
    - reportingMessage: Message detailing the reason for the report.
    """
    html_content = render_to_string('report_admin.html', {
      'reportingUser': reportingUser,
      'userReported': userReported,
      'reportingMessage': reportingMessage,
      'url': url
    })
    send_mail(
      subject='REPORT',
      message=f'This user { reportingUser }, reported this user { userReported }, slug post { url } Rerporting message: { reportingMessage }',
      from_email=FROM_EMAIL,
      recipient_list=[ADMIN],
      html_message=html_content
    )

  def notify_reporting(self, reportingUser, url):
    """
    Sends an email notification to the user who made the report, confirming that their report has been received.
    ----------    
    Parameters:
    - reportingUser: Email of the user who made the report.
    - url: URL slug of the reported sale.
    """
    html_content = render_to_string('notify_reporting.html', {
      'reportingUser': reportingUser,
      'url': url
    })
    send_mail(
      subject='SALE REPORTED',
      message=f"""Hello, { reportingUser } we are very sorry that you had a bad experience with one of our users,
      we will review your case as soon as possible and you will be notified about the status of this operation { url }, 
      do not panic, we have everything under control and we will solve it in less than 24 hours. cryptoexchange team.""",
      from_email=FROM_EMAIL,
      recipient_list=[reportingUser],
      html_message=html_content
    )

  def put(self, request, format=None):
    data = request.data
    slug = data.get('slug')
    reportingMessage = data.get('message')
    sale = get_object_or_404(Sale, slug=slug)
    if sale.status in ['taked_offer', 'bought']:
      # AQUI SE REPORTA A EL COMPRADOR
      if sale.user == request.user:
        profile = get_object_or_404(Profile, user=sale.buyer)
        profile.reports += 1
        profile.save()
        self.report_email(reportingUser=request.user.email , userReported=sale.buyer.email, url=slug, reportingMessage=reportingMessage)
        self.notify_reporting(reportingUser=request.user.email, url=slug)
        sale.status = 'reported'
        sale.save()
        return Response({f'User {request.user}':  f'reported to {sale.buyer.email}'}, status=status.HTTP_200_OK)
      elif sale.buyer == request.user:
        # AQUI SE REPORTA A EL VENDEDOR
        profile = get_object_or_404(Profile, user=sale.user)
        profile.reports += 1
        profile.save()
        self.report_email(reportingUser=sale.buyer.email, userReported=sale.user.email, url=slug, reportingMessage=reportingMessage)
        self.notify_reporting(reportingUser=sale.buyer.email, url=slug)
        sale.status = 'reported'
        sale.save()
        return Response({f'User {request.user}':  f'reported to {sale.user.email}'}, status=status.HTTP_200_OK)
      return Response({'error': 'You are not the buyer or the seller of this post'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({'error', sale.status}, status=status.HTTP_403_FORBIDDEN)

class PauseSalePost(APIView):
  """
  API endpoint to pause a sale post by updating its status.
  --------------
  Only authenticated users can access this endpoint.

  Handle PUT request to pause a sale post.

  Expects a JSON payload with 'slug' field.

  Preconditions:
  - Sale instance must have a status of 'active' or 'pending'.
  - The requesting user must be the owner of the sale post.

  Process:
  - Fetch the Sale instance using the provided 'slug'.
  - Verify the status and ownership conditions.
  - Update the sale status to 'paused'.

  Returns:
  - 200 OK: If the sale post was successfully paused.
  - 304 NOT_MODIFIED: If the sale status is not 'active' or 'pending', or if the user is not the owner.
  """
  
  permission_classes = (permissions.IsAuthenticated, )
  
  def put(self, request, format=None):
    data = request.data
    slug = data.get('slug')
    sale = get_object_or_404(Sale, slug=slug)
    if sale.status in ['active', 'pending'] and sale.user == request.user:
      sale.status = 'paused'
      sale.save()
      return Response({'success': 'status paused', 'status': sale.status}, status=status.HTTP_200_OK)
    return Response({"error": sale.status}, status=status.HTTP_304_NOT_MODIFIED)

class EditSalePost(APIView):
  """
  API endpoint to edit a sale post.
  ------------
  Only authenticated users can access this endpoint.

  Handle PUT request to edit a sale post.

  Expects a JSON payload with 'slug' field and other editable fields ('bankEntity', 'reference', 'accountNumber')

  Preconditions:
  - The requesting user must be the owner of the sale post.
  - Sale post must be in 'paused' status to make changes.

  Process:
  - Fetch the Sale instance using the provided 'slug'.
  - Verify ownership and status conditions.
  - If valid and sale address has confirmed transaction, change status to 'active'.
  - If address has no transaction, change status to 'pending'.
  - Save changes using the serializer.

  Returns:
  - 200 OK: If the sale post was successfully edited.
  - 400 Bad Request: If the serializer is not valid.
  - 401 Unauthorized: If the user is not the owner of the sale post.
  - 500 Internal Server Error: If there was an error processing the request.
  """

  permission_classes = (permissions.IsAuthenticated, )

  def put(self, request, format=None):
    data = request.data
    slug = data.get('slug')
    sale = get_object_or_404(Sale, slug=slug)
    serializer = EditeSaleSerializer(sale, data=request.data, partial=True)
    if sale.user == request.user:
      if serializer.is_valid() and sale.status == 'paused':
        try:
          getUTXO = requests.get(url=f'https://mempool.space/testnet/api/address/{sale.address}/utxo')
          dataInfo = getUTXO.json()
          if dataInfo:
            if dataInfo[0]["status"]["confirmed"] == True:
              print("Address have ammount")
              print(str(dataInfo[0]["txid"]), int(dataInfo[0]["vout"]), int(dataInfo[0]["value"]))
              sale.status = 'active'
              sale.save()
          else:
            print("There is not transaction")
            sale.status = 'pending'
            sale.save()
        except Exception as e:
          Response({'error': e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        serializer.save()
        return Response(sale.status, status=status.HTTP_200_OK)
      return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response({'error', 'You are not the creator of this post'}, status=status.HTTP_401_UNAUTHORIZED)
# ----------------------------------------- GET -------------------------------------------------
class GetSaleList(APIView):
  permission_classes = [permissions.IsAuthenticated]
  def get(self, request, format=None):
    # Filtra las ventas por estado 'active'
    sales = Sale.objects.filter(status='active').values('address', 'bankEntity', 'created_at', 'slug')
    sales_list = list(sales)
    return Response(sales_list, status=status.HTTP_200_OK)

class GetDashboardOwnertList(APIView):
  permission_classes = [permissions.IsAuthenticated]
  def get(self, request, format=None):
    user = request.user
    sales = Sale.objects.filter(user=user)
    if not sales:
      return Response(status=status.HTTP_204_NO_CONTENT)
    serialized_data = DashboardPostListSerializer(sales, many=True)
    return Response(serialized_data.data, status=status.HTTP_200_OK)

class GetSale(APIView):
  permission_classes = [permissions.IsAuthenticated]
  def get(self, request, format=None):
    slug = request.query_params.get('slug')
    sale = get_object_or_404(Sale, slug=slug)
    serializer = SaleGetAllSerializer(sale)
    return Response(serializer.data, status=status.HTTP_200_OK)
  
class GetSaleOwnerPost(APIView):
  permission_classes = [permissions.IsAuthenticated]
  def get(self, request, format=None):
    slug = request.query_params.get('slug')
    sale = get_object_or_404(Sale, slug=slug)
    if sale.user == request.user:
      serializer = SaleGetAllSerializer(sale)
      return Response(serializer.data, status=status.HTTP_200_OK)
    return Response({'error'}, status=status.HTTP_401_UNAUTHORIZED)

class GetPurchasedSalesList(APIView):
  permission_classes = [permissions.IsAuthenticated]

  def get(self, request, format=None):
    user = self.request.user
    purchases = Sale.objects.filter(buyer=user)
    if not purchases.exists():
      return Response({"detail": "No purchased sales found."}, status=status.HTTP_204_NO_CONTENT)
    serialized_data = SaleListPurchaedSerializer(purchases, many=True)
    return Response(serialized_data.data, status=status.HTTP_200_OK)

# 32983c62-6273-462b-9ee4-310d1a10fe6a
# m/32/98/36'/262'/734'/62/94
# tb1qty2w4ktv2jshjv4r8erddqgw3flkt7qzt4rqwp
# {
#     "cryptocurrency": "Bitcoin",
#     "symbol": "BTCTEST",
#     "network": "testnet",
#     "strength": 256,
#     "entropy": "066b83177a1c08ea73553cc929593651b7be88fb2538d11d997fdfe7462e03de",
#     "mnemonic": "all foster shift vintage scene inside snap pole since enlist eternal pet know dutch uncle poem speed under garment save inner blade author snack",
#     "language": "english",
#     "passphrase": "ZtTcJPaq1cPUqYQ",
#     "seed": "dc0ea0203a5552d496ee6eb0ce59d1dca0d83718c0cbcf2f07b9f8cb4d964c91d6215b981098666e25ece3aea1c08ef787d02b2d4b75bf9f865281e29c7deab5",
#     "root_xprivate_key": "vprv9DMUxX4ShgxMMG8T9qymUkMYEgPiPEgMh7gxs1aSaEmbXYjnPS8eR89h5Dn7DSVs6WhYEK8384RRiWexjURxswaoQR8N7zpFaHn2g5eKina",
#     "root_xpublic_key": "vpub5SLqN2bLY4WeZkCvFsWmqtJGniECnhQD4LcZfPz48aJaQM4vvyStxvUAvVV6Td5YyMWNNxQY5Nbscby3JLhmwbSTFK4oKGrEeV44JKdWpxC",
#     "xprivate_key": "vprv9TwUUZNyTZfHczkGGRqmFuMbn5wmPnT29PVkfFvJ5X27DWTZZtLH51eKRCbJoEm8Wxgvm2m6pvKZuYF3MVXkTRFJJZaBQNizMoXv23ftXAm",
#     "xpublic_key": "vpub5gvpt4usHwDaqUpjNTNmd3JLL7nFoFAsWcRMTeKudrZ66Jni7ReXcoxoGVA3LCiAmwqoZxXV6DgcB2e1i5AX5MdgSbydPS2b5yzhb2FugdD",
#     "uncompressed": "54ccee9ff2b648bf6d74bf3a80e113346ed100f4c77895bee56c6fc0c0c8e1dec8136f764b6a260116efb9a19600da791147b9b353774374745686d94c8bc4dd",
#     "compressed": "0354ccee9ff2b648bf6d74bf3a80e113346ed100f4c77895bee56c6fc0c0c8e1de",
#     "chain_code": "1fb066136ee75ee13116ded0f2ba8f8c8b23f71f5ab8ad54b7753ed733004727",
#     "private_key": "8aca325c3913e5947f88b7177ee20c4806e2edd591dcfb42651bf5857295b827",
#     "public_key": "0354ccee9ff2b648bf6d74bf3a80e113346ed100f4c77895bee56c6fc0c0c8e1de",
#     "wif": "cSEVRm4aH2rQuGAGte3ZL9JmfdKkR1gwChxBebrk5xHQYjNAGVoY",
#     "finger_print": "cc482014",
#     "semantic": "p2wpkh",
#     "path": "m/0/0/0'/0'/0'/0/0",
#     "hash": "cc482014bac0e6697013861af0569f594d9df0df",
#     "addresses": {
#         "p2pkh": "mz96YYQQpdg13v8Tcg2XfhtYKzsdRJ6ANA",
#         "p2sh": "2MtcnHsjLWXHhiaatrUksXzD4jTgRicf1j2",
#         "p2wpkh": "tb1qe3yzq996crnxjuqnscd0q45lt9xemuxlc6uhmh",
#         "p2wpkh_in_p2sh": "2N1DgK4pCsidm9xCXMMNcUpuMJZAX5jG7Ji",
#         "p2wsh": "tb1qn07r9jxwhapufy0z886a2zlajpgp79ttaturduy6mlt4gxfpr48qeycfjj",
#         "p2wsh_in_p2sh": "2N5ERfKm6KcYmwpUWCr7WjCmVKwNEEDfTxP"
#     }
# }