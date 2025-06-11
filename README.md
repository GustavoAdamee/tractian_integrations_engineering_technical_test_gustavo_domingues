# TracOS ↔ Client Integration Service

An asynchronous Python service that enables bidirectional work order synchronization between Tractian's CMMS (TracOS) and customer ERP systems.

## Architecture Overview

This integration service follows a modular, extensible architecture designed to handle multiple customer integrations without modifying core components.

### Core Components

- **Processors**: Handle the main business logic for inbound and outbound flows
- **Handlers**: Manage data operations for TracOS (MongoDB) and Customer systems (File-based)
- **Translator**: Manages data transformation between different system formats
- **Main**: Orchestrates the entire synchronization pipeline

### System Architecture

![System Architecture](assets/tractian_challange.drawio.svg)

<!-- Add your flow diagram here -->

## Project Structure

```
tractian_integrations_engineering_technical_test/
├── src/
│   ├── main.py                    # Application entry point
│   ├── core/                      # Core business logic
│   │   ├── customer_handler.py    # Customer system operations
│   │   ├── tracos_handler.py      # TracOS MongoDB operations
│   │   └── translator.py          # Data transformation logic
│   └── processors/                # Flow processors
│       ├── inbound_processor.py   # Customer → TracOS flow
│       └── outbound_processor.py  # TracOS → Customer flow
├── data/
│   ├── inbound/                   # Input JSON files from customer
│   └── outbound/                  # Output JSON files to customer
├── tests/                         # Tests with pytest
├── setup.py                       # Sample data generator
├── docker-compose.yml             # MongoDB container setup
├── pyproject.toml                 # Poetry dependencies
└── README.md                      # Original requirements
```

## Data Flow

### Inbound Flow (Customer → TracOS)
1. **Read** JSON files from `data/inbound/` directory
2. **Validate** required fields (orderNo, status, dates)
3. **Translate** customer format to TracOS format
4. **Store/Update** work orders in MongoDB
5. **Log** processing results

### Outbound Flow (TracOS → Customer)
1. **Query** MongoDB for unsynced work orders (`isSynced: false`)
2. **Translate** TracOS format to customer format
3. **Generate** JSON files in `data/outbound/` directory
4. **Mark** work orders as synced in MongoDB
5. **Log** synchronization results

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose**
- **Poetry** (for dependency management)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tractian_integrations_engineering_technical_test_gustavo_domingues
   ```

2. **Install dependencies**
   ```bash
   # Install Poetry if needed
   curl -sSL https://install.python-poetry.org | python3 -
   
   # Install project dependencies
   poetry install
   ```

3. **Start MongoDB**
   ```bash
   docker-compose up -d mongodb
   ```

4. **Initialize sample data**
   ```bash
   poetry run python setup.py
   ```

### Configuration

Set environment variables or create a `.env` file:

```bash
# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017
MONGO_DATABASE=tractian
MONGO_COLLECTION=workorders
MONGO_MAX_RETRIES=3
MONGO_RETRY_DELAY=1.0

# Data Directories
DATA_INBOUND_DIR=data/inbound
DATA_OUTBOUND_DIR=data/outbound
```

## Running the Application

### Basic Execution
```bash
# Run the complete integration pipeline
poetry run python src/main.py
```

### Docker Setup
```bash
# Start MongoDB service
docker-compose up -d

# Verify MongoDB is running
docker ps
```

### MongoDB Compass (Recommended)

**MongoDB Compass** is a powerful GUI tool that makes it easy to visualize, query, and manage your MongoDB data during development.

#### Installation

- **Download MongoDB Compass**
   - Visit: https://www.mongodb.com/try/download/compass


#### Connecting to Your Local MongoDB

1. **Open MongoDB Compass**
2. **Connection String**: Use the default connection or enter:
   ```
   mongodb://localhost:27017
   ```
3. **Click Connect**

#### Using Compass with This Project

Once connected, you can:
- **Browse Collections**: Navigate to `tractian` database → `workorders` collection
- **View Documents**: See all work orders in a user-friendly format
- **Query Data**: Filter work orders by status, dates, or any field
- **Monitor Changes**: Watch real-time updates as the integration runs
- **Export Data**: Export collections for backup or analysis

#### Useful Queries for Development

```javascript
// Find unsynced work orders
{ "isSynced": false }

// Find orders by status
{ "status": "IN_PROGRESS" }

// Find recent orders
{ "createdAt": { "$gte": new Date("2024-01-01") } }
```

## Testing

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src

# Run specific test file
poetry run pytest tests/test_integration.py -v

# Run with detailed output
poetry run pytest -v -s
```

### Test Coverage
- **End-to-end integration tests**
- **Unit tests for core components**
- **Mock external dependencies**
- **Error handling scenarios**


## Key Features

### Resilience & Error Handling
- **Retry Logic**: MongoDB operations with configurable retry attempts
- **Connection Recovery**: Automatic reconnection on database failures
- **Graceful Degradation**: Continue processing on individual record failures
- **Comprehensive Logging**: Structured logging with loguru

### Data Validation
- **Required Field Validation**: Ensures critical fields are present
- **Format Validation**: Validates date formats and data types
- **Status Mapping**: Proper translation between system status values

### Extensibility
- **Modular Design**: Easy to add new customer integrations
- **Handler Pattern**: Swap data sources without changing business logic
- **Configuration-Driven**: Customize behavior via environment variables

## Future Enhancements!

- **REST API Interface**: HTTP endpoints for external integration
- **Real-time Synchronization**: WebSocket or message queue integration
- **Multi-tenant Support**: Handle multiple customer configurations
- **Advanced Retry Strategies**: Exponential backoff, circuit breakers
- **Metrics Dashboard**: Monitoring and alerting capabilities
- **Data Validation Rules**: Configurable business rules engine
