from django.urls import path
from .views import *

urlpatterns = [
  path('create/', CreateSalePostView.as_view()),                     # CREA UN POST
  path('active-sale/', ActiveSaleLoop.as_view()),                    # LLAMAR A ESTA FUNCION DESPUES DE CREAR UN POST
  path('looking/', ChangeToLooking.as_view()),                       # CAMBIA EL ESTADO A 'looking'
  path('loop-change/', ChangeToAtiveLoop.as_view()),                 # REVISA SI EL USUARIO QUE MIRA (looking) YA TOMO LA OFERTA O COMPRÓ
  path('take-offer/', Buy.as_view()),                                # CAMBIA EL STATUS A TOMADO 'taked_offer'
  path('report/', ReportPost.as_view()),                             # REPORTA A EL VENDEDOR Y/O COMPRADOR
  path('confirm-buy/', ConfirmBuy.as_view()),                        # CONFIRMA LA COMPRA EL CREADOR DEL POST
  path('pause/', PauseSalePost.as_view()),                           # PAUSA EL POST PARA PODERLO EDITAR DESPUES
  path('edit/', EditSalePost.as_view()),                             # EDITA EL POST
  path('comment/', MakeComment.as_view()),                           # HACE COMMENTARIOS
  path('get-sale-list', GetSaleList.as_view()),                      # OBTENER TODOS LOS POST CON DATOS ESPECIFICOS Y RETORNARLOS
  path('get-dashboard-owned-list', GetDashboardOwnertList.as_view()),# OBTENER TODOS LOS POST CREADOS CON DATOS ESPECIFICOS Y RETORNARLOS
  path('get-purchases-list', GetSaleOwnerPost.as_view()),            # OBTENER LAS COMPRAS DEL USUARIO Y RETORNA SI ESTA COMENTADO O NO
  path('get', GetSale.as_view()),                                    # OBTENER TODOS LOS DATOS DE UN MODELO CON UN SLUG COMO PARAMETRO
  #     /get?slug=your-slug-value
  path('get-confirm', GetSaleOwnerPost.as_view()),                   # OBTENER TODOS LOS DATOS DEL MODELO CON UN SLUG COMO PARAMETRO
  #     /get-confirm?slug=your-slug-value
]