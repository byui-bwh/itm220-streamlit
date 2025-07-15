# Getting Started with Streamlit (via pipx)

This guide helps you get started with [Streamlit](https://streamlit.io/), a powerful framework for building data apps in Python — using `pipx` for isolated installs.

---

## 🚀 Prerequisites

You’ll need:

- Python 3.8 or later
- `pip` and `pipx` (Python package and app manager)

---

## 🔧 Step 1: Install Python and pip

### Windows

1. Download and install Python from [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
   - ✅ Check **"Add Python to PATH"** during installation
2. Verify:
   ```bash
   python --version
   pip --version

### 🍎 macOS (with Homebrew)

    brew install python
    python3 --version
    pip3 --version

### 🐧 Linux (Ubuntu/Debian)

    sudo apt update
    sudo apt install python3 python3-pip
    python3 --version
    pip3 --version

## ⚙️ Step 2: Install pipx

pipx is a tool to install and run Python CLI apps in isolated environments.

1. Open Terminal.

2. Run the following:

        python3 -m pip install --user pipx
        python3 -m pipx ensurepath
        

3. Restart your terminal (or log out and back in).

4. Verify:

        pipx --version

## 📦 Step 3: Install Streamlit with pipx

1. In Terminal, run:

        pipx install streamlit
        pipx runpip streamlit install -r requirements.txt

2. Confirm Streamlit is installed:

        streamlit --version

## ✅ Step 4: Run the Streamlit Demo

1. In Terminal, run:

        streamlit hello

2. This will open a browser window showing an interactive Streamlit demo app.

## 🛠 Step 5: Create Your First Streamlit App

1. Create a new file named app.py:

        import streamlit as st

        st.title("Hello, Streamlit!")
        st.write("This is your first Streamlit app using pipx.")

2. Run it:

        streamlit run app.py

3. Your browser will open and show your custom app.
