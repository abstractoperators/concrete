# Setup

This guide will take you through environment setup in order to run the codebase locally and contribute to our project.
It's recommended that you use MacOS, Unix, or Linux as an operating system for development; we do not support nor provide instructions for Windows systems and development.

## [Github Repository](https://github.com)

```shell
# HTTPS
git clone https://github.com/abstractoperators/concrete.git

# SSH
git clone git@github.com:abstractoperators/concrete.git
```

## [Python](https://www.python.org)

### [Pyenv](https://github.com/pyenv/pyenv)

Pyenv allows you to manage multiple versions of Python on your computer.
It can configure a default Python version globally or on a directory basis.

> We recommend following the official instructions on the Pyenv Github repository for
[Installation](https://github.com/pyenv/pyenv?tab=readme-ov-file#installation),
completing the entire block before skipping to [Python Version](#python-version).

Alternatively, you can follow our abridged instructions here:

```shell
curl https://pyenv.run | bash  # to install Pyenv
```

For **bash**:

```shell
echo -e 'export PYENV_ROOT="$HOME/.pyenv"\nexport PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo -e 'eval "$(pyenv init --path)"\n eval "$(pyenv init -)"' >> ~/.bashrc  # to set up environment variables
```

For **zsh**:

```shell
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
```

And finally for both:

```shell
exec "$SHELL"  # restarts the terminal shell process
```

### Python Version
After you've installed Pyenv, we can install the required version of Python:

```shell
pyenv install 3.11  # install latest Python 3.11.

pyenv global 3.11

# Alternatively, to set in a particular directory where the projects will be built
# cd /Users/personmcpersonsonson/git/concreteproject
# pyenv local 3.11
```

> `concrete` requires a minimum of Python 3.11.9 to be installed.

## [Poetry](https://python-poetry.org)

Concrete uses poetry for dependency management and environment isolation.

> Again, we recommend following the official
[installation instructions](https://python-poetry.org/docs/#installing-with-the-official-installer).

Otherwise, run the following:

```shell
curl -sSL https://install.python-poetry.org | python3 -
```

By default, poetry as a command should be accessible.
If not, you'll need to manually add it to your path.

For example, on MacOS systems:

```shell
# bash
echo -e 'export PATH="~/Library/Application Support/pypoetry/venv/bin/poetry:$PATH"' >> ~/.bashrc

# zsh
echo -e 'export PATH="~/Library/Application Support/pypoetry/venv/bin/poetry:$PATH"' >> ~/.zshrc
```

For Linux/Unix:

```shell
# bash
echo -e 'export PATH="~/.local/share/pypoetry/venv/bin/poetry"' >> ~/.bashrc

# zsh
echo -e 'export PATH="~/.local/share/pypoetry/venv/bin/poetry"' >> ~/.zshrc
```

In addition to package and dependency management, we use Poetry to augment the developer git workflow.
The following command will install the correct dependencies to run `concrete` locally as well as the precommit packages to pass our PR validations.
In the root folder of the repository:

```shell
make install
```

If you find yourself needing to run the pre-commit manually, use the following:

```shell
poetry run pre-commit run --all-files
```

and to skip pre-commit hooks for whatever reason, use

```shell
git commit -m "Pass butter" --no-verify
```

## Environment Variables

We recommend you store all of the relevant environment variables into a `.env` file
located in the root directory of `concrete`.
A full `.env` developer example can be found [in our repository](https://github.com/abstractoperators/concrete/blob/02cc58605f5b0b507434985ef2bd3ed7bb7e3881/.env.example).

Be sure to set the `ENV` variable as necessary:

```shell
ENV=DEV
# for development
```

or

```shell
ENV=PRODUCTION
# for production
```

### [OpenAI](https://openai.com/index/openai-api/)

By default, operators rely on OpenAI ChatGPT 4 models to process queries. OpenAI requires a key to access its API:

```shell
OPENAI_API_KEY=<your api key here>
```
