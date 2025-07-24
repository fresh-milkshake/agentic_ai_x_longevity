![header](assets/header.png)

![Build](https://github.com/fresh-milkshake/agentic_ai_x_longevity/actions/workflows/gh-pages.yml/badge.svg)
![License](https://img.shields.io/github/license/fresh-milkshake/agentic_ai_x_longevity)
![Hackathon](https://img.shields.io/badge/Agentic%20AI%20X%20Longevity-Hackathon-lightgreen)
![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
<a href="README.md">
   ![Russian](https://img.shields.io/badge/Russian%20version%20of%20README-README.md-blue)
</a>

# Agentic AI x Longevity - Ligand-Protein Interaction Dataset

This project creates an extracted dataset of ligand-protein binding interactions in CSV format with required fields. The dataset is generated using an API for patent search, followed by processing and data extraction.

The project uses [uv](https://docs.astral.sh/uv/) for dependency and project management. Code formatting and linting is handled by [ruff](https://github.com/astral-sh/ruff).

## Usage

> [!IMPORTANT]
> The project requires an API key from USPTO PatentsView. You can obtain one [here](https://patentsview-support.atlassian.net/servicedesk/customer/portal/1/group/1/create/18). Applications are typically approved within 1-2 days.

### Dependencies Installation

Required dependencies:
- [Python 3.13](https://www.python.org/downloads/release/python-3130/) (versions 3.10+ are supported)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [Ollama](https://ollama.ai/)

You'll need to choose an appropriate model for text processing. The project uses the `qwen3` model by default. To download it, run:

```bash
ollama pull qwen3
```

#### Running the Project

1. Clone the repository:
   ```bash
   git clone https://github.com/fresh-milkshake/agentic_ai_x_longevity
   ```

2. Install Python dependencies using `uv` (or `poetry`):
   ```bash
   uv sync
   ```

> [!NOTE]
> You can install `uv` using `pip`:
>
> ```bash
> pip install uv
> ```

3. Create a `.env` file based on `.env.example` in the project root and add your USPTO API key:
   ```bash
   USPTO_API_KEY=your_api_key
   ```

   In the future, I plan to find and add the ability to work without API keys if possible, to make the project more accessible.

4. Run the script:
   ```bash
   uv run main.py
   ```
   or
   ```bash
   python main.py
   ```
   When using python directly, ensure you're running from a virtual environment with all Python dependencies installed.

#### Running Gradio UI

> [!WARNING]
> Not all Gradio UI functions are fully debugged and may work incorrectly. For the best experience, it's recommended to use the standard project launch via `uv run main.py`.

The project uses Gradio to create a user-friendly web interface with the ability to run various project stages both individually and in a unified pipeline.

To launch the interface, run:

```bash
uv run gradio-ui.py
```

#### Running Intermediate Results Review Script

To review intermediate results in pickle file format created during agent processing, you can use the TUI script:

```bash
uv run interactive_view_pkl.py
```

## Project Structure

```
├── patents/                 # Patents (PDF)
│   └── *.pdf                # Patent documents
├── results/                 # Processing results
│   ├── intermediate/        # Intermediate data
│   │   └── *.pkl            # Serialized data from agents
│   ├── final/               # Final results
│   │   └── *.csv            # CSV files with results
│   └── raw/                 # Raw data
│       └── *.txt            # Text versions of documents
├── src/                     # Main code
│   ├── constants            # Project constants and settings
│   │   └── ...
│   ├── evaluation           # Dataset evaluation script
│   │   └── ...
│   ├── filtering            # Patent search and download from USPTO
│   │   └── ...
│   ├── processing           # Data processing
│   │   ├── pipeline.py      # Main AI agents pipeline
│   │   └── ...
│   ├── orchestration        # Orchestrator
│   │   └── ...
│   ├── models.py            # ML models for use in agents
│   └── utils.py             # Helper functions for agents
├── main.py                  # Entry point
├── gradio-ui.py             # Gradio web interface
├── pyproject.toml
├── README.md 
├── README_EN.md             # This file
├── .env.example
└── .env
```

## AI Pipeline Architecture

The project uses a multi-agent AI system for processing patent documents:

### Agent Types

1. **SearcherAgent**: Determines if text contains ligand-protein interactions
   - Analyzes text for presence of interaction parameters (Ki, IC50, Kd, EC50)
   - Returns confidence score for interaction detection

2. **BioinfAgent**: Extracts ligand-protein interaction data
   - Identifies ligands and proteins
   - Extracts interaction parameters
   - Provides interaction context and type

3. **SupervisorAgent**: Validates extraction results
   - Checks output correctness
   - Identifies fixable errors
   - Provides improvement suggestions

4. **FixAgent**: Corrects identified issues
   - Fixes extraction errors based on supervisor feedback
   - Ensures data quality and consistency

### Processing Pipeline

```
PDF Patent → Text Extraction → Page Analysis → 
SearcherAgent → BioinfAgent → SupervisorAgent → 
FixAgent (if needed) → CSV Output
```

## Data Output Format

The system generates CSV files with the following columns:

- `page_number`: Page number in the source document
- `ligand`: Name or identifier of the ligand
- `protein`: Name or identifier of the protein
- `interaction_type`: Type of interaction (binding, inhibition, etc.)
- `context`: Quote or context from the text
- `Ki`: Inhibition constant
- `IC50`: Half maximal inhibitory concentration
- `Kd`: Dissociation constant
- `EC50`: Half maximal effective concentration

## Web Interface Features

The Gradio interface provides:

### Text Processing Tab
- Direct text input for analysis
- File upload support (.txt, .md)
- Real-time interaction extraction
- Detailed results with parameters

### Patent Management Tab
- USPTO patent downloading with configurable queries
- Project statistics dashboard
- Full pipeline execution
- PDF file downloads with size information

### Results Tab
- Interactive data tables
- Individual CSV file downloads
- Combined export functionality
- File management and statistics

## Technical Requirements

- **Python**: 3.10+ (3.13+ recommended)
- **Memory**: 4GB+ RAM recommended for processing
- **Storage**: Variable depending on patent collection size
- **Network**: Internet connection for USPTO API access

## Contributing

This project was developed for the Agentic AI x Longevity Hackathon. Contributions are welcome!

## License

This project is published under the MIT License. See [LICENSE](LICENSE.txt) for details.

## Acknowledgments

- USPTO PatentsView API for patent data access
- Ollama for local LLM inference
- Gradio for the web interface framework
- The Agentic AI x Longevity Hackathon organizers