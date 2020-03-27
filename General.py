import sublime
import sublime_plugin

class CloseMinimapOnMultiView(sublime_plugin.EventListener):
    was_minimap_open = True

    def on_post_window_command(self, window, cmd_name, _args):
        if cmd_name in ['set_layout', 'new_pane', 'close_pane']:
            if len(window.get_layout()['cols']) > 2:
                # save the state of the minimap so that we can conditionally restore it when back to 1 column
                self.was_minimap_open = window.is_minimap_visible()
                window.set_minimap_visible(False)
            else:
                window.set_minimap_visible(self.was_minimap_open)