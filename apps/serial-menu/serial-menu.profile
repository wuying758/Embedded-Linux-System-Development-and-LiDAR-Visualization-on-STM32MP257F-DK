# Start the serial menu only on the board's serial login console.
# SSH sessions and other terminals retain the normal shell.
if [ -t 0 ] && [ -t 1 ]; then
    case "$(tty 2>/dev/null)" in
        /dev/ttySTM0)
            if [ -x /usr/local/bin/hello_world_example ]; then
                /usr/local/bin/hello_world_example
            fi
            ;;
    esac
fi
