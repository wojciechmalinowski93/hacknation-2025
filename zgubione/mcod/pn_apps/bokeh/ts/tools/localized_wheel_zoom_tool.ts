import {WheelZoomTool, WheelZoomToolView} from "models/tools/gestures/wheel_zoom_tool"
import * as p from "core/properties"

export namespace LocalizedWheelZoomTool {
  export type Attrs = p.AttrsOf<Props>

  export type Props = WheelZoomTool.Props & {localized_tool_name: p.Property<string>}

}

export interface LocalizedWheelZoomTool extends LocalizedWheelZoomTool.Attrs {}

export class LocalizedWheelZoomTool extends WheelZoomTool{
  properties: LocalizedWheelZoomTool.Props
  __view_type__: WheelZoomToolView

  constructor(attrs?: Partial<LocalizedWheelZoomTool.Attrs>) {
    super(attrs)
    this.tool_name = this.localized_tool_name
  }

  static init_LocalizedWheelZoomTool(): void {
    this.prototype.default_view = WheelZoomToolView

    this.define<LocalizedWheelZoomTool.Props>({
      localized_tool_name: [ p.String ],
    })
  }

  get tooltip(): string {
    return this.tool_name
  }

}
