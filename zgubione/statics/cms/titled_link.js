const ModalWorkflowSource = window.draftail.ModalWorkflowSource;
const Modifier = window.DraftJS.Modifier;
const EditorState = window.DraftJS.EditorState;
const AtomicBlockUtils = window.DraftJS.AtomicBlockUtils
const RichUtils = window.DraftJS.RichUtils
const ENTITY_TYPE = window.Draftail.ENTITY_TYPE;
const TooltipEntity = window.draftail.TooltipEntity;
const React = window.React

const $ = global.jQuery;

const EMBED = 'EMBED';
const DOCUMENT = 'DOCUMENT';
const TITLED_LINK = 'TITLED_LINK';
const EMAIL_LINK = 'EMAIL_LINK';

const Icon = window.wagtail.components.Icon;

const LINK_ICON = React.createElement(Icon, {name: 'link'});
const BROKEN_LINK_ICON = React.createElement(Icon, {name: 'warning'});
const MAIL_ICON = React.createElement(Icon, {name:'mail'});

const getEmailAddress = mailto => mailto.replace('mailto:', '').split('?')[0];
const getPhoneNumber = tel => tel.replace('tel:', '').split('?')[0];
const getDomainName = url => url.replace(/(^\w+:|^)\/\//, '').split('/')[0];

const MUTABILITY = {};
MUTABILITY[ENTITY_TYPE.LINK] = 'MUTABLE';
MUTABILITY[TITLED_LINK] = 'MUTABLE';
MUTABILITY[EMAIL_LINK] = 'MUTABLE';
MUTABILITY[DOCUMENT] = 'MUTABLE';
MUTABILITY[ENTITY_TYPE.IMAGE] = 'IMMUTABLE';
MUTABILITY[EMBED] = 'IMMUTABLE';

const getSelectedBlocksList = (editorState) => {
  const selectionState = editorState.getSelection();
  const content = editorState.getCurrentContent();
  const startKey = selectionState.getStartKey();
  const endKey = selectionState.getEndKey();
  const blockMap = content.getBlockMap();
  const blocks =  blockMap
    .toSeq()
    .skipUntil((_, k) => k === startKey)
    .takeUntil((_, k) => k === endKey)
    .concat([[endKey, blockMap.get(endKey)]]);
  return blocks.toList();
};

/**
* Returns the currently selected text in the editor.
* See https://github.com/jpuri/draftjs-utils/blob/e81c0ae19c3b0fdef7e0c1b70d924398956be126/js/block.js#L106.
*/
const getSelectionText = (editorState) => {
  const selection = editorState.getSelection();
  let start = selection.getAnchorOffset();
  let end = selection.getFocusOffset();
  const selectedBlocks = getSelectedBlocksList(editorState);

  if (selection.getIsBackward()) {
    const temp = start;
    start = end;
    end = temp;
  }

  let selectedText = '';
  for (let i = 0; i < selectedBlocks.size; i += 1) {
    const blockStart = i === 0 ? start : 0;
    const blockEnd = i === (selectedBlocks.size - 1) ? end : selectedBlocks.get(i).getText().length;
    selectedText += selectedBlocks.get(i).getText().slice(blockStart, blockEnd);
  }

  return selectedText;
};

const getChooserConfig = (entityType, entity, selectedText) => {
  let url;
  let urlParams;
  let defaultUrl;

  switch (entityType.type) {
  case ENTITY_TYPE.IMAGE:
    return {
      url: `${global.chooserUrls.imageChooser}?select_format=true`,
      urlParams: {},
      onload: global.IMAGE_CHOOSER_MODAL_ONLOAD_HANDLERS,
    };

  case EMBED:
    return {
      url: global.chooserUrls.embedsChooser,
      urlParams: {},
      onload: global.EMBED_CHOOSER_MODAL_ONLOAD_HANDLERS,
    };

  case ENTITY_TYPE.LINK:
    url = global.chooserUrls.pageChooser;
    urlParams = {
      page_type: 'wagtailcore.page',
      allow_external_link: true,
      allow_email_link: true,
      allow_phone_link: true,
      allow_anchor_link: true,
      link_text: selectedText,
    };

  case TITLED_LINK:
    defaultUrl = global.chooserUrls.externalLinkChooser;
    url = defaultUrl;
    urlParams = {
      page_type: 'wagtailcore.page',
      allow_external_link: true,
      allow_email_link: true,
      allow_phone_link: true,
      allow_anchor_link: true,
      link_text: selectedText,
    };

    if (entity) {
      const data = entity.getData();
      urlParams.link_title = data.link_title;
      if (data.id) {
        if (data.parentId !== null) {
          url = `${defaultUrl}${data.parentId}/`;
        } else {
          url = defaultUrl;
        }
      } else if (data.url.startsWith('mailto:')) {
        url = global.chooserUrls.emailLinkChooser;
        urlParams.link_url = data.url.replace('mailto:', '');
      } else if (data.url.startsWith('tel:')) {
        url = global.chooserUrls.phoneLinkChooser;
        urlParams.link_url = data.url.replace('tel:', '');
      } else if (data.url.startsWith('#')) {
        url = global.chooserUrls.anchorLinkChooser;
        urlParams.link_url = data.url.replace('#', '');
      } else {
        url = defaultUrl;
        urlParams.link_url = data.url;
      }
    }

    return {
      url,
      urlParams,
      onload: global.PAGE_CHOOSER_MODAL_ONLOAD_HANDLERS,
    };

  case EMAIL_LINK:
    url = global.chooserUrls.emailLinkChooser;
    urlParams = {
      page_type: 'wagtailcore.page',
      allow_external_link: true,
      allow_email_link: true,
      allow_phone_link: true,
      allow_anchor_link: true,
      link_text: selectedText,
    };

    if (entity) {
      const data = entity.getData();
      urlParams.link_title = data.link_title;
      if (data.id) {
        if (data.parentId !== null) {
          url = `${global.chooserUrls.emailLinkChooser}${data.parentId}/`;
        } else {
          url = global.chooserUrls.emailLinkChooser;
        }
      } else if (data.url.startsWith('mailto:')) {
        url = global.chooserUrls.emailLinkChooser;
        urlParams.link_url = data.url.replace('mailto:', '');
      } else if (data.url.startsWith('tel:')) {
        url = global.chooserUrls.phoneLinkChooser;
        urlParams.link_url = data.url.replace('tel:', '');
      } else if (data.url.startsWith('#')) {
        url = global.chooserUrls.anchorLinkChooser;
        urlParams.link_url = data.url.replace('#', '');
      } else {
        url = global.chooserUrls.externalLinkChooser;
        urlParams.link_url = data.url;
      }
    }

    return {
      url,
      urlParams,
      onload: global.PAGE_CHOOSER_MODAL_ONLOAD_HANDLERS,
    };

  case DOCUMENT:
    return {
      url: global.chooserUrls.documentChooser,
      urlParams: {},
      onload: global.DOCUMENT_CHOOSER_MODAL_ONLOAD_HANDLERS,
    };

  default:
    return {
      url: null,
      urlParams: {},
      onload: {},
    };
  }
};

const filterEntityData = (entityType, data) => {
  switch (entityType.type) {
  case ENTITY_TYPE.IMAGE:
    return {
      id: data.id,
      src: data.preview.url,
      alt: data.alt,
      format: data.format,
    };
  case EMBED:
    return {
      embedType: data.embedType,
      url: data.url,
      providerName: data.providerName,
      authorName: data.authorName,
      thumbnail: data.thumbnail,
      title: data.title,
    };
  case ENTITY_TYPE.LINK:
    if (data.id) {
      return {
        url: data.url,
        id: data.id,
        parentId: data.parentId,
      };
    }

    return {
      url: data.url,
    };
  case TITLED_LINK:
    if (data.id) {
      return {
        url: data.url,
        id: data.id,
        parentId: data.parentId,
        link_title: data.link_title,
      };
    }

    return {
      url: data.url,
      link_title: data.link_title
    };

  case EMAIL_LINK:
    if (data.id) {
      return {
        url: data.url,
        id: data.id,
        parentId: data.parentId,
        link_title: data.link_title,
      };
    }

    return {
      url: data.url,
      link_title: data.link_title
    };

  case DOCUMENT:
    return {
      url: data.url,
      filename: data.filename,
      id: data.id,
    };
  default:
    return {};
  }
};

class ExtendedModalWorkflowSource extends ModalWorkflowSource{

  constructor(props) {
    super(props);
  }

  componentDidMount() {
    const { onClose, entityType, entity, editorState } = this.props;
    let dr = window.draftail;
    const selectedText = getSelectionText(editorState);
    const { url, urlParams, onload } = getChooserConfig(entityType, entity, selectedText);

    $(document.body).on('hidden.bs.modal', this.onClose);

    // eslint-disable-next-line new-cap
    this.workflow = global.ModalWorkflow({
      url,
      urlParams,
      onload,
      responses: {
        imageChosen: this.onChosen,
        // Discard the first parameter (HTML) to only transmit the data.
        embedChosen: (_, data) => this.onChosen(data),
        documentChosen: this.onChosen,
        pageChosen: this.onChosen,
      },
      onError: () => {
        // eslint-disable-next-line no-alert
        window.alert(global.wagtailConfig.STRINGS.SERVER_ERROR);
        onClose();
      },
    });
  }

  onChosen(data) {
    const { editorState, entityType, onComplete } = this.props;
    const content = editorState.getCurrentContent();
    const selection = editorState.getSelection();

    const entityData = filterEntityData(entityType, data);
    const mutability = MUTABILITY[entityType.type];
    const contentWithEntity = content.createEntity(entityType.type, mutability, entityData);
    const entityKey = contentWithEntity.getLastCreatedEntityKey();

    let nextState;

    if (entityType.block) {
      // Only supports adding entities at the moment, not editing existing ones.
      // See https://github.com/springload/draftail/blob/cdc8988fe2e3ac32374317f535a5338ab97e8637/examples/sources/ImageSource.js#L44-L62.
      // See https://github.com/springload/draftail/blob/cdc8988fe2e3ac32374317f535a5338ab97e8637/examples/sources/EmbedSource.js#L64-L91
      nextState = AtomicBlockUtils.insertAtomicBlock(editorState, entityKey, ' ');
    } else {
      // Replace text if the chooser demands it, or if there is no selected text in the first place.
      const shouldReplaceText = data.prefer_this_title_as_link_text || selection.isCollapsed();

      if (shouldReplaceText) {
        // If there is a title attribute, use it. Otherwise we inject the URL.
        const newText = data.title || data.url;
        const newContent = Modifier.replaceText(content, selection, newText, null, entityKey);
        nextState = EditorState.push(editorState, newContent, 'insert-characters');
      } else {
        nextState = RichUtils.toggleLink(editorState, selection, entityKey);
      }
    }

    // IE11 crashes when rendering the new entity in contenteditable if the modal is still open.
    // Other browsers do not mind. This is probably a focus management problem.
    // From the user's perspective, this is all happening too fast to notice either way.
    this.workflow.close();

    onComplete(nextState);
  }

}




// Determines how to display the link based on its type: page, mail, anchor or external.
const getLinkAttributes = (data) => {
  const url = data.url || null;
  let icon;
  let label;

  if (!url) {
    icon = BROKEN_LINK_ICON;
    label = global.wagtailConfig.STRINGS.BROKEN_LINK;
  } else if (data.id) {
    icon = LINK_ICON;
    label = url;
  } else if (url.startsWith('mailto:')) {
    icon = MAIL_ICON;
    label = getEmailAddress(url);
  } else if (url.startsWith('tel:')) {
    icon = LINK_ICON;
    label = getPhoneNumber(url);
  } else if (url.startsWith('#')) {
    icon = LINK_ICON;
    label = url;
  } else {
    icon = LINK_ICON;
    label = getDomainName(url);
  }

  return {
    url,
    icon,
    label,
  };
};

/**
 * Represents a link within the editor's content.
 */
const TitledLink = props => {
  const { entityKey, contentState } = props;
  const data = contentState.getEntity(entityKey).getData();

  return React.createElement(TooltipEntity,
      {...props, ...getLinkAttributes(data)}
    );
};

window.draftail.registerPlugin({
    type: 'TITLED_LINK',
    source: ExtendedModalWorkflowSource,
    decorator: TitledLink,
});

window.draftail.registerPlugin({
    type: 'EMAIL_LINK',
    source: ExtendedModalWorkflowSource,
    decorator: TitledLink,
});
