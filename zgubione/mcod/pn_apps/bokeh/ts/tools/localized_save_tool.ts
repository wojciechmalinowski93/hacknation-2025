import {SaveTool, SaveToolView} from "models/tools/actions/save_tool"
import * as p from "core/properties"

export namespace LocalizedSaveTool {
  export type Attrs = p.AttrsOf<Props>

  export type Props = SaveTool.Props & {localized_tool_name: p.Property<string>}

}

export interface LocalizedSaveTool extends LocalizedSaveTool.Attrs {}

export class LocalizedSaveTool extends SaveTool{

  constructor(attrs?: Partial<SaveTool.Attrs>) {
    super(attrs)
    this.tool_name = this.localized_tool_name
  }

  static init_LocalizedSaveTool(): void {
    this.prototype.default_view = SaveToolView

    this.define<LocalizedSaveTool.Props>({
      localized_tool_name: [ p.String ],
    })
  }
}
