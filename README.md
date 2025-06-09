# Cruise Reservation V2 🛳️

**Cruise Reservation V2** é a segunda versão do sistema distribuído para reservas de cruzeiros, desenvolvido como projeto para a disciplina de **Sistemas Distribuídos** da UTFPR.

A V2 evolui com:

- Interface Web completa (HTML + JS + TailwindCSS)
- Microsserviços com API REST + eventos assíncronos (RabbitMQ)
- Suporte a notificações em tempo real via SSE
- Protótipo de experiência de reserva com fluxo simplificado: consulta → reserva → pagamento → bilhete → cancelamento

---

## 🧱 Microsserviços

| Serviço         | Função                                                                 |
|----------------|------------------------------------------------------------------------|
| **MS Itinerários** | Gerencia destinos e disponibilidade de cabines (REST + RabbitMQ)         |
| **MS Reserva**     | Cria, cancela e gerencia reservas (REST + eventos `reserva-*`)         |
| **MS Pagamento**   | Gera links e processa pagamentos (REST + eventos `pagamento-*`)        |
| **MS Bilhete**     | Gera bilhetes após pagamento aprovado                                  |
| **MS Marketing**   | Publica promoções para clientes interessados                           |
| **MS Notifica**    | Envia eventos via SSE por canal exclusivo por cliente                  |
| **Frontend**       | Interface Web com TailwindCSS + APIs REST + SSE                        |

---

## 🎨 Frontend (TailwindCSS + JS)

- Consulta de itinerários (com destino, preço e cabines restantes)
- Efetuar reserva e receber link de pagamento
- Cancelar reserva
- Registrar/cancelar interesse em promoções
- Receber notificações de promoções (SSE)
- Páginas separadas:
  - `index.html`: home + reservas (com TailwindCSS)
  - `pagamento.html`: confirmar/cancelar pagamento (simulando webhook de serviço de pagamento externo)
  - `minhas_reservas.html`: listar e cancelar reservas
  - `notificacoes.html`: notificações em tempo real por cliente

---

## 🚀 Execução Manual

1. **RabbitMQ ativo em `localhost:5672`**
2. Instalar dependências:
   ```bash
   pip install flask flask-cors pika requests
   ```
3. Iniciar cada MS:
   ```bash
   python3 MS_itinerarios.py
   python3 MS_reserva.py
   python3 MS_pagamento.py
   python3 MS_bilhete.py
   python3 MS_marketing.py
   python3 MS_notifica.py
   ```
4. Iniciar frontend:
   ```bash
   python3 frontend_server.py
   ```

---

## ✅ Fluxo de Reserva

1. Usuário acessa `index.html` e seleciona um destino
2. Cria reserva → link de pagamento gerado
3. Acessa `pagamento.html`, confirma ou recusa pagamento
4. Se aprovado → bilhete gerado e enviado via SSE
5. Se recusado ou cancelado → cabine liberada

---

## 📄 Licença

MIT License

---

**Desenvolvido por:**  
Samuel Canuto Sales de Oliveira – 2025  
Giulia Cavasin – 2025
