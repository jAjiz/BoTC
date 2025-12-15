# BoTCoin 🤖💰

Bot de trading automatizado para criptomonedas con integración a Kraken y notificaciones por Telegram.

## 📋 Descripción

BoTCoin es un sistema de trading algorítmico diseñado para operar en el exchange Kraken de manera automatizada. Utiliza estrategias basadas en ATR (Average True Range) para gestionar posiciones con trailing stops dinámicos, permitiendo maximizar ganancias mientras limita las pérdidas.

El bot incluye dos estrategias de trading configurables y ofrece control remoto completo a través de un bot de Telegram, permitiendo monitorear y gestionar operaciones en tiempo real desde cualquier dispositivo.

## ✨ Características Principales

- **Trading Automatizado**: Ejecuta operaciones de compra/venta automáticamente basándose en condiciones de mercado
- **Dos Estrategias de Trading**:
  - **Multipliers**: Estrategia basada en multiplicadores de ATR con márgenes mínimos
  - **Rebuy**: Estrategia de recompra con distancias de activación ajustables
- **Trailing Stops Dinámicos**: Protección de beneficios mediante stops que se ajustan automáticamente
- **Gestión de Riesgo**:
  - Control de asignación mínima de activos
  - Recalibración automática basada en volatilidad (ATR)
  - Protección contra operaciones que desequilibren el portfolio
- **Integración con Telegram**:
  - Notificaciones en tiempo real de todas las operaciones
  - Comandos para consultar estado, mercado y posiciones
  - Pausar/reanudar el bot remotamente
- **Persistencia de Estado**: Guarda el estado de posiciones para continuar tras reinicios
- **Multi-Par**: Soporte para operar múltiples pares de criptomonedas simultáneamente

## 🏗️ Arquitectura

```
BoTCoin/
├── main.py                 # Punto de entrada principal y lógica del bot
├── core/                   # Módulos principales
│   ├── config.py          # Configuración y variables de entorno
│   ├── logging.py         # Sistema de logs
│   └── state.py           # Gestión de estado persistente
├── exchange/              # Integración con exchanges
│   └── kraken.py         # API de Kraken
├── strategies/            # Estrategias de trading
│   ├── multipliers.py    # Estrategia con multiplicadores
│   └── rebuy.py          # Estrategia de recompra
├── services/              # Servicios externos
│   └── telegram.py       # Bot de Telegram
└── requirements.txt       # Dependencias Python
```

## 🚀 Instalación

### Requisitos Previos

- Python 3.8 o superior
- Cuenta en Kraken con API Key y Secret
- Bot de Telegram (crear con [@BotFather](https://t.me/botfather))
- Tu User ID de Telegram (obtener con [@userinfobot](https://t.me/userinfobot))

### Pasos de Instalación

1. **Clonar el repositorio**:
```bash
git clone https://github.com/jAjiz/BoTCoin.git
cd BoTCoin
```

2. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno**:

Crear un archivo `.env` en la raíz del proyecto con el siguiente contenido:

```env
# Credenciales de Kraken API
KRAKEN_API_KEY=tu_api_key_de_kraken
KRAKEN_API_SECRET=tu_api_secret_de_kraken

# Credenciales de Telegram Bot
TELEGRAM_TOKEN=tu_token_de_telegram
ALLOWED_USER_ID=tu_user_id_de_telegram

# Configuración del Bot
MODE=rebuy                    # Opciones: "rebuy" o "multipliers"
SLEEPING_INTERVAL=60          # Intervalo entre sesiones (segundos)
ATR_DATA_DAYS=60             # Días de datos históricos para calcular ATR
POLL_INTERVAL_SEC=20         # Intervalo de polling de Telegram

# Pares de Trading (separados por comas)
PAIRS=XBTEUR,ETHEUR

# Parámetros de Trading (globales)
K_ACT=4.5                    # Multiplicador de activación
K_STOP_SELL=2.5              # Multiplicador de stop para ventas
K_STOP_BUY=2.5               # Multiplicador de stop para compras
MIN_MARGIN=0.01              # Margen mínimo (1%)

# Asignación Mínima de Activos (por par)
MIN_ALLOCATION_XBTEUR=0.5    # 50% mínimo en BTC
MIN_ALLOCATION_ETHEUR=0.3    # 30% mínimo en ETH

# Parámetros Específicos por Par (opcional)
# K_ACT_XBTEUR=5.0
# K_STOP_SELL_XBTEUR=3.0
# K_STOP_BUY_XBTEUR=3.0
```

## ⚙️ Configuración

### Estrategias de Trading

#### Estrategia "Multipliers"
Esta estrategia utiliza multiplicadores de ATR para establecer niveles de activación y stop loss, con un margen mínimo garantizado para proteger las ganancias.

- **Distancia de Activación**: `K_ACT × ATR`
- **Stop Loss**: `K_STOP × ATR` (limitado por margen mínimo)
- **ATR Mínimo**: Calculado automáticamente basándose en `MIN_MARGIN / (K_ACT - K_STOP)`

#### Estrategia "Rebuy"
Esta estrategia añade un componente fijo basado en el precio de entrada, ideal para recompras escalonadas.

- **Distancia de Activación**: 
  - Venta: `K_STOP_SELL × ATR + 1.06% × Precio_Entrada`
  - Compra: `K_STOP_BUY × ATR + 0.1% × Precio_Entrada`
- **Stop Loss**: `K_STOP × ATR`

### Parámetros Clave

- **K_ACT**: Controla la distancia de activación del trailing stop
- **K_STOP_SELL/K_STOP_BUY**: Controlan la distancia del stop loss
- **MIN_MARGIN**: Margen mínimo de beneficio garantizado (%)
- **MIN_ALLOCATION**: Porcentaje mínimo del activo que debe mantenerse

### Configuración por Par

Puedes personalizar parámetros para pares específicos añadiendo el nombre del par como sufijo:

```env
K_ACT_XBTEUR=5.0
K_STOP_SELL_XBTEUR=3.0
MIN_ALLOCATION_XBTEUR=0.5
```

## 🎮 Uso

### Iniciar el Bot

```bash
python main.py
```

El bot comenzará a monitorear los pares configurados y ejecutará operaciones según la estrategia seleccionada.

### Comandos de Telegram

Una vez iniciado, puedes controlar el bot desde Telegram:

- `/status` - Estado del bot y pares configurados
- `/pause` - Pausar operaciones del bot
- `/resume` - Reanudar operaciones
- `/market [par]` - Ver datos actuales del mercado
- `/positions [par]` - Ver posiciones abiertas
- `/help` - Mostrar ayuda con comandos disponibles

**Ejemplos**:
```
/market XBTEUR
/positions
/pause
```

## 🔄 Flujo de Operación

1. **Monitoreo**: El bot consulta precios actuales y ATR cada intervalo configurado
2. **Detección de Órdenes Cerradas**: Identifica órdenes ejecutadas en Kraken
3. **Creación de Posiciones**: Por cada orden cerrada, crea una posición con trailing stop
4. **Activación**: Cuando el precio alcanza el nivel de activación, se activa el trailing stop
5. **Trailing**: El stop se ajusta dinámicamente siguiendo el precio favorable
6. **Cierre**: Cuando el precio alcanza el stop, se ejecuta la orden de cierre
7. **Recalibración**: El ATR se recalcula periódicamente para ajustar los stops a la volatilidad actual

### Gestión de Riesgo

- **Protección de Inventario**: Evita ventas que reduzcan el activo por debajo del mínimo configurado
- **Consolidación de Posiciones**: Fusiona automáticamente posiciones similares cercanas
- **Recalibración Dinámica**: Ajusta stops cuando el ATR varía más del ±20%

## 📊 Estrategias en Detalle

### Ejemplo: Estrategia Multipliers

Supongamos:
- Precio BTC: 50,000€
- ATR actual: 1,000€
- K_ACT: 4.5
- K_STOP: 2.5
- MIN_MARGIN: 1%

**Compra ejecutada a 50,000€**:
- Nueva posición: SELL (contraria)
- Activación: 50,000 + (4.5 × 1,000) = 54,500€
- Cuando precio ≥ 54,500€:
  - Trailing activo
  - Stop inicial: 54,500 - (2.5 × 1,000) = 52,000€
  - Margen garantizado: 500€ (1% de 50,000€)

Si el precio sube a 56,000€:
- Nuevo trailing: 56,000€
- Nuevo stop: 56,000 - 2,500 = 53,500€ (limitado por margen mínimo)

## 🗂️ Estructura de Datos

### Estado de Posiciones

El bot mantiene un archivo `data/trailing_state.json` con información de todas las posiciones:

```json
{
  "XBTEUR": {
    "ORDER_ID": {
      "mode": "rebuy",
      "created_time": "2025-12-15 10:30:00",
      "opening_order": ["ORDER_ID"],
      "side": "sell",
      "entry_price": 50000.0,
      "volume": 0.1,
      "cost": 5000.0,
      "activation_atr": 1000.0,
      "activation_price": 54500.0,
      "activation_time": "2025-12-15 11:00:00",
      "trailing_price": 56000.0,
      "stop_atr": 1000.0,
      "stop_price": 53500.0
    }
  }
}
```

### Posiciones Cerradas

Las posiciones cerradas se guardan en `data/closed_positions.json` con información completa del PnL y órdenes asociadas.

## 🚦 Deployment

El repositorio incluye una configuración de GitHub Actions (`.github/workflows/deploy.yml`) para despliegue automático mediante SSH. El workflow se ejecuta automáticamente al hacer push a la rama `main`.

### Configuración de Secrets

Para habilitar el deployment automático, configura estos secrets en GitHub:

- `VM_IP`: Dirección IP del servidor
- `VM_USER`: Usuario SSH
- `VM_KEY`: Clave privada SSH

## 📝 Logs y Monitoreo

- Los logs se almacenan en `logs/`
- Cada operación importante se registra y notifica por Telegram
- Emojis distintivos para cada tipo de evento:
  - 🆕 Nueva posición creada
  - 🔀 Posiciones fusionadas
  - ⚡ Trailing stop activado
  - 📈 Precio trailing actualizado
  - ♻️ Recalibración de ATR
  - ⛔ Posición cerrada
  - 💸 Resultado PnL
  - 🛡️ Operación bloqueada por protección

## 🔒 Seguridad

- **Nunca** compartas tu `.env` ni lo subas a GitHub (está en `.gitignore`)
- Usa permisos de API de Kraken limitados (solo trading, no withdrawals)
- Mantén tu ALLOWED_USER_ID privado para evitar acceso no autorizado al bot de Telegram
- Revisa regularmente los logs para detectar comportamientos anómalos

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## ⚠️ Disclaimer

Este software se proporciona "tal cual", sin garantías de ningún tipo. El trading de criptomonedas conlleva riesgos significativos y puedes perder tu inversión. Usa este bot bajo tu propia responsabilidad y considera empezar con pequeñas cantidades para probar el sistema.

**No somos responsables de pérdidas financieras derivadas del uso de este software.**

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## 👤 Autor

**jAjiz**

- GitHub: [@jAjiz](https://github.com/jAjiz)

## 🙏 Agradecimientos

- [Kraken](https://www.kraken.com/) - Exchange de criptomonedas
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Librería de Telegram
- [krakenex](https://github.com/veox/python3-krakenex) - Cliente de API de Kraken

---

**⭐ Si este proyecto te resulta útil, considera darle una estrella en GitHub!**
