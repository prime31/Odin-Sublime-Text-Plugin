# Odin-Sublime-Text-Plugin

Syntax highlighting, autocompletion, and Goto Symbol/Anything/Definition for the Odin language in Sublime Text 3. This is held together but a bit of spit and duct tape but it may provide a modicum of assistance for helping to learn/use Odin. Note that the build commands will only work if the `odin` executable is globally available in your PATH.


## Installation
Download or clone this repo into your Sublime Text 3 Packages folder (found via Preferences -> Browse Packages). It must be cloned into a folder named `Odin`: `git clone https://github.com/prime31/Odin-Sublime-Text-Plugin.git Odin`


## Setup
By default, the plugin uses the path `~/odin` to locate the Odin shared and core folders. You can override this by adding the following to your Sublime settings file: `"odin_install_path": "your/path/to/odin"`

**Package auto import**: By default, the plugin will prompt to auto import packages if you type the package name followed by ".". You can disable this behaviour by adding `"odin_prompt_for_package_import": false` to your Sublime preferences file.

**vcvarsall**: (Windows only) By default, the Visual Studio x64 environment vars will be sourced from here: `C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat`. You can override that by adding `'vc_vars_path'` to your Sublime preferences with the path to the batch file.


## Usage
Just type code like usual and you should get valid completions as you type. There are a few additional tools included with the plugin:
- `text transformations`: select some text and right-click and there will be a few options in the `Text Transformations` section for converted to ada case/snake case.
- `sublime sidebar`: right-clicking files/folders there will be some extra options such as duplicating items, opening items in Finder/Terminal and a few other handy helpers


## Build Support
- `odin`: standard build. This will gather all libs (dylib or DLL files) present in the `odin/shared` subfolders and pass them to the executable when it is run after building. Note that libs must be in a subfolder called `native` for the time being. You can have as many `native` folders nested anywhere under `odin/shared`.
- `odin - Build With Opt Level 3`: appends `-opt=3` to the standard build command
- `odin - Print args`: same as standard build but dumps the build command used to the Sublime console for inspection of lib paths
- `odin - apitrace`: same as standard build but launches the built executable with `apitrace`. Note that `apitrace` must be available on your path. This will output a `.trace` file with the same name as the executable. You can then right-click the `.trace` file in the Sublime file manager and choose the `Open with qapitrace` option to open it.


## Makefile support
There is an additional build command for Makefiles. If you have a Makefile open and you run the Sublime `Build with...` command you will see an option for `Odin-Make`. This allows you to have a Makefile in any subfolder in your project which differs from the default Sublime Makefile support which requires that there is a single Makefile at the root of your project.


## Acknowledgements
This whole plugin started out as a copy of [JaiTools](https://github.com/RobinWragg/JaiTools), since Jai and Odin are fairly similar.
