{-# LANGUAGE DeriveAnyClass #-}
{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE DerivingStrategies #-}
{-# LANGUAGE OverloadedStrings #-}
module ChildB (MsgB (..), childB) where

import GHC.Generics (Generic)
import Miso
import qualified Miso.Html as H
import Miso.JSON (FromJSON, ToJSON)
import Miso.String (ms)

-- This child can be reused with a different outgoing message adapter.
newtype MsgB = MsgB Int
  deriving stock (Eq, Show, Generic)
  deriving anyclass (ToJSON, FromJSON)

data ActionB = SendB

childB
  :: ToJSON message
  => (MsgB -> message)
  -> Component context () Int ActionB
childB toParent = component 0 updateB viewB
  where
    updateB SendB = do
      modify (+ 1)
      mailParent (toParent (MsgB 7))

    viewB sent = H.section_ []
      [ H.button_ [textProp "id" "send-b", H.onClick SendB] [text "Send B (7)"]
      , H.p_ [] [text "Child B sends: ", H.span_ [textProp "id" "child-b-sent"] [text (ms sent)]]
      ]
