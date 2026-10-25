def reveal_workspace_control(page: Page, selector: str | Locator) -> Locator:
    """Reach a global control through the actual mobile navigation when needed."""
    control = page.locator(selector) if isinstance(selector, str) else selector
    if control.count() and control.evaluate("node => Boolean(node.closest('#workspaceSidebar'))"):
        hidden = not control.is_visible() or control.evaluate(
            "node => Boolean(node.closest('[inert], [hidden], [aria-hidden=\"true\"]'))"
        )
        if hidden:
            toggle = page.locator('#workspaceNavToggle')
            expect(toggle).to_be_visible()
            if toggle.get_attribute('aria-expanded') != 'true':
                toggle.click()
    expect(control).to_be_visible()
    expect(control).to_be_enabled()
    assert not control.evaluate(
        "node => Boolean(node.closest('[inert], [hidden], [aria-hidden=\"true\"]'))"
    ), f'{selector} remains inside hidden or inert navigation'
    control.click(trial=True)
    expect(control).to_be_in_viewport()
    return control
