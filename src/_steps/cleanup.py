__all__ = ("cleanup",)


def cleanup(ctx):
    ctx.temp_zipfile.close()
    ctx.temp_dir.cleanup()
